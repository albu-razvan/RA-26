import time
import os

import noisereduce as nr
import numpy as np
import torch
from pyannote.audio import Pipeline


class OSDDetector:
    def __init__(
        self,
        hf_token,
        sample_rate,
        lag_offsets_ms,
        residual_boost,
        max_gain,
        lag_step_ms,
        use_denoise,
        min_overlap_total_s,
    ):
        self.sample_rate = sample_rate
        self.lag_offsets_ms = lag_offsets_ms
        self.residual_boost = residual_boost
        self.max_gain = max_gain
        self.lag_step_ms = lag_step_ms
        self.use_denoise = use_denoise
        self.min_overlap_total_s = min_overlap_total_s
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/overlapped-speech-detection",
            use_auth_token=hf_token,
        )
        try:
            torch.set_num_threads(int(os.environ.get("TORCH_NUM_THREADS", "1")))
            torch.set_num_interop_threads(
                int(os.environ.get("TORCH_NUM_INTEROP_THREADS", "1"))
            )
        except Exception as exception:
            print("[OSD] Torch thread config skipped: {}".format(exception))
        self.pipeline.to(torch.device("cpu"))
        print("[OSD] Pipeline loaded")

    def detect_overlap(self, audio_i16, robot_template_i16, robot_tts_start_time):
        try:
            audio_f = audio_i16.astype(np.float32) / 32768.0

            if robot_template_i16 is not None:
                template = robot_template_i16.astype(np.float32) / 32768.0
                elapsed = time.time() - robot_tts_start_time
                start_idx = int(elapsed * self.sample_rate) - audio_f.shape[0]
                win_len = audio_f.shape[0]

                lag_max = int((self.lag_offsets_ms / 1000.0) * self.sample_rate)
                step = int((self.lag_step_ms / 1000.0) * self.sample_rate)
                lags = list(range(-lag_max, lag_max + 1, step))
                if 0 not in lags:
                    lags.append(0)

                best_resid = None
                best_resid_rms = None
                for lag in lags:
                    t_start = start_idx + lag
                    t_end = t_start + win_len
                    if t_start < 0 or t_end > template.shape[0]:
                        continue

                    tmpl = template[t_start:t_end]
                    denom = float(np.dot(tmpl, tmpl) + 1e-8)
                    scale = float(np.dot(audio_f, tmpl) / denom)
                    resid = audio_f - scale * tmpl
                    resid_rms = float(np.sqrt(np.mean(resid**2)) + 1e-9)

                    if best_resid_rms is None or resid_rms < best_resid_rms:
                        best_resid_rms = resid_rms
                        best_resid = resid

                if best_resid is not None:
                    audio_f = np.clip(best_resid * self.residual_boost, -1.0, 1.0)

            rms = float(np.sqrt(np.mean(audio_f**2)) + 1e-9)
            target_rms = 0.12
            gain = min(target_rms / rms, self.max_gain)
            audio_f = np.clip(audio_f * gain, -1.0, 1.0)

            if self.use_denoise:
                audio_f = nr.reduce_noise(
                    y=audio_f,
                    sr=self.sample_rate,
                    stationary=True,
                    prop_decrease=0.8,
                )

            waveform = torch.from_numpy(audio_f.astype(np.float32)).unsqueeze(0)
            osd = self.pipeline({"waveform": waveform, "sample_rate": self.sample_rate})
            segments = list(osd.get_timeline().support())

            total = sum(max(0.0, seg.end - seg.start) for seg in segments)
            if segments:
                print("[OSD] overlap segments={} total={:.3f}s".format(len(segments), total))

            return total >= self.min_overlap_total_s
        except Exception as exception:
            print("[OSD] Detection failed: {}".format(exception))
            return False
