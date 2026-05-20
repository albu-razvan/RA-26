import collections
import threading
import time

import numpy as np
import webrtcvad

import state

from audio_pipeline.constants import (
    FRAME_SIZE_BYTES,
    MIN_UTTERANCE_BYTES,
    OSD_CHECK_AFTER_ROBOT_START_S,
    OSD_CHECK_INTERVAL_FRAMES,
    OSD_HITS_REQUIRED_IN_WINDOW,
    OSD_HIT_WINDOW_SIZE,
    OSD_MIN_AUDIO_SAMPLES,
    OSD_WINDOW_FRAMES,
    OVERLAP_BASELINE_DELTA,
    OVERLAP_BASELINE_HISTORY_MIN,
    OVERLAP_CHECK_AFTER_ROBOT_START_S,
    OVERLAP_CHECK_INTERVAL_FRAMES,
    OVERLAP_CHECK_WINDOW_FRAMES,
    OVERLAP_LAG_OFFSETS_MS,
    OVERLAP_MIN_ABS_RESIDUAL_RATIO,
    RING_BUFFER_FRAMES,
    RMS_THRESHOLD,
    SAMPLE_RATE,
    SILENCE_LIMIT_FRAMES,
    SPEECH_START_THRESHOLD,
)
from audio_pipeline.debug_audio import DebugAudioRecorder
from service_clients import (
    animate_pepper,
    get_controller_status,
    interrupt_pepper,
    is_game_not_started,
    set_pepper_state,
)
from speech import (
    DEBUG_AUDIO_RECORD,
    DEBUG_AUDIO_RECORD_CHUNK_SECONDS,
    DEBUG_AUDIO_RECORD_DIR,
)


class AudioProcessor:
    def __init__(self, osd_detector, stt_transcriber):
        self.vad = webrtcvad.Vad(3)
        self.buffer = b""
        self.osd_detector = osd_detector
        self.stt_transcriber = stt_transcriber

        self.triggered = False
        self.ring_buffer = collections.deque(maxlen=RING_BUFFER_FRAMES)

        self.silence_counter = 0
        self.cooldown_frames = 0
        self.speech_start_threshold = SPEECH_START_THRESHOLD
        self.consecutive_speech = 0
        self.current_utterance_bytes = 0

        self.overlap_mic_buffer = collections.deque(maxlen=OVERLAP_CHECK_WINDOW_FRAMES)
        self.overlap_check_frames_accum = 0
        self.overlap_best_ratio_history = collections.deque(maxlen=6)
        self.last_robot_tts_start_time = 0.0

        self.osd_mic_buffer = collections.deque(maxlen=OSD_WINDOW_FRAMES)
        self.osd_check_frames_accum = 0
        self.osd_inflight = False
        self.osd_lock = threading.Lock()
        self.osd_pending_audio = None
        self.osd_pending_token = 0.0
        self.osd_overlap_history = collections.deque(maxlen=OSD_HIT_WINDOW_SIZE)

        self.captured_version = 0

        self.debug_audio = DebugAudioRecorder(
            enabled=DEBUG_AUDIO_RECORD,
            output_dir=DEBUG_AUDIO_RECORD_DIR,
            chunk_seconds=DEBUG_AUDIO_RECORD_CHUNK_SECONDS,
            sample_rate=SAMPLE_RATE,
        )

    def process_stream(self, raw_chunk):
        self.debug_audio.append(raw_chunk)

        if all(v == 0 for v in raw_chunk[:100]):
            self.cooldown_frames = 30
            return None

        self.buffer += raw_chunk

        while len(self.buffer) >= FRAME_SIZE_BYTES:
            frame = self.buffer[:FRAME_SIZE_BYTES]
            self.buffer = self.buffer[FRAME_SIZE_BYTES:]

            if self.cooldown_frames > 0:
                self.cooldown_frames -= 1
                continue

            self._process_frame(frame)

        return None

    def _process_frame(self, frame):
        try:
            data_np = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
            front_int16 = data_np.astype(np.int16).tobytes()
            rms_front = np.sqrt(np.mean(data_np.astype(np.float32) ** 2))

            is_robot_speaking = state.robot_is_speaking or (
                time.time() < state.robot_ignore_vad_until
            )
            is_vad_speech = self.vad.is_speech(front_int16, SAMPLE_RATE)
            is_speech = is_vad_speech and rms_front > RMS_THRESHOLD

            if is_robot_speaking:
                self._handle_robot_speaking(front_int16, is_vad_speech, rms_front)
            else:
                self._handle_robot_not_speaking()

            if not self.triggered:
                self._handle_waiting_for_speech(front_int16, is_robot_speaking, is_speech)
            else:
                self._handle_active_utterance(front_int16, is_speech)
        except Exception as exception:
            print("Frame processing error: {}".format(exception))

    def _handle_robot_speaking(self, front_int16, is_vad_speech, rms_front):
        if state.robot_tts_start_time != self.last_robot_tts_start_time:
            self.last_robot_tts_start_time = state.robot_tts_start_time
            self._reset_overlap_tracking()

        self.overlap_mic_buffer.append(front_int16)
        self.overlap_check_frames_accum += 1

        if self.overlap_check_frames_accum >= OVERLAP_CHECK_INTERVAL_FRAMES:
            self.overlap_check_frames_accum = 0
            if state.robot_tts_pcm_16k is not None:
                overlap_hit = self.check_robot_user_overlap_fast()
                if overlap_hit and (is_vad_speech or rms_front > (RMS_THRESHOLD * 0.25)):
                    print("[OVERLAP] Detected user overlap - interrupting")
                    self.trigger_barge()

        self.osd_mic_buffer.append(front_int16)
        self.osd_check_frames_accum += 1
        if (
            len(self.osd_mic_buffer) > 0
            and self.osd_check_frames_accum >= OSD_CHECK_INTERVAL_FRAMES
        ):
            self.osd_check_frames_accum = 0
            token = state.robot_tts_start_time
            audio_i16 = np.frombuffer(b"".join(list(self.osd_mic_buffer)), dtype=np.int16)

            if audio_i16.size < OSD_MIN_AUDIO_SAMPLES:
                return

            with self.osd_lock:
                if self.osd_inflight:
                    self.osd_pending_audio = audio_i16
                    self.osd_pending_token = token
                else:
                    self.osd_inflight = True
                    self.osd_pending_audio = None
                    self._start_osd_job(audio_i16, token)

    def _handle_robot_not_speaking(self):
        self.overlap_mic_buffer.clear()
        self.overlap_check_frames_accum = 0
        self.osd_mic_buffer.clear()
        self.osd_check_frames_accum = 0
        self.osd_overlap_history.clear()
        with self.osd_lock:
            self.osd_pending_audio = None

    def _handle_waiting_for_speech(self, front_int16, is_robot_speaking, is_speech):
        if is_robot_speaking:
            # Do not accumulate speech-trigger counters from robot playback.
            # Otherwise, the first frame after playback can immediately trip VAD.
            self.consecutive_speech = 0
            self.ring_buffer.clear()
            return

        self.ring_buffer.append(front_int16)

        if is_speech:
            self.consecutive_speech += 1
        else:
            self.consecutive_speech = 0

        if self.consecutive_speech < self.speech_start_threshold:
            return

        if not self.stt_transcriber.is_ready_for_new_utterance():
            self.consecutive_speech = 0
            return

        print("[VAD] Voice detected")

        status = get_controller_status(timeout=0.2)
        self.captured_version = status.get("state_version", 0)

        if is_game_not_started(status):
            self.consecutive_speech = 0
            self.ring_buffer.clear()
            return

        state.current_version = self.captured_version
        state.is_user_talking = True

        try:
            interrupt_pepper(timeout=1)
            state.robot_is_speaking = False
            set_pepper_state("listening", timeout=1)
            animate_pepper("listen", timeout=1)
        except Exception as exception:
            print("Error changing state: {}".format(exception))

        self.triggered = True
        self.current_utterance_bytes = 0
        if not self.stt_transcriber.start_utterance(self.captured_version):
            self.triggered = False
            self.current_utterance_bytes = 0
            return

        for buffered_frame in self.ring_buffer:
            self.stt_transcriber.feed_audio(buffered_frame)
            self.current_utterance_bytes += len(buffered_frame)
        self.ring_buffer.clear()
        self.consecutive_speech = 0

    def _handle_active_utterance(self, front_int16, is_speech):
        self.stt_transcriber.feed_audio(front_int16)
        self.current_utterance_bytes += len(front_int16)

        if not is_speech:
            self.silence_counter += 1
        else:
            self.silence_counter = 0

        if self.silence_counter <= SILENCE_LIMIT_FRAMES:
            return

        print("[VAD] Processing audio chunk...")
        state.is_user_talking = False

        try:
            set_pepper_state("processing", timeout=1)
            animate_pepper("stand", timeout=1)
        except Exception as exception:
            print("Error changing state: {}".format(exception))

        self.triggered = False
        self.silence_counter = 0

        if self.current_utterance_bytes < MIN_UTTERANCE_BYTES:
            self.stt_transcriber.cancel_last_utterance()
            self.current_utterance_bytes = 0
            return

        self.stt_transcriber.mark_utterance_end()
        self.current_utterance_bytes = 0

    def _start_osd_job(self, audio_i16: np.ndarray, token: float):
        threading.Thread(
            target=self._run_osd_job,
            args=(audio_i16, token),
            daemon=True,
        ).start()

    def _run_osd_job(self, audio_i16: np.ndarray, token: float):
        try:
            if not state.robot_is_speaking:
                return
            if state.robot_tts_start_time != token:
                return
            if self.osd_detector is None:
                return
            if time.time() - state.robot_tts_start_time < OSD_CHECK_AFTER_ROBOT_START_S:
                return

            overlap = self.osd_detector.detect_overlap(
                audio_i16,
                robot_template_i16=state.robot_tts_pcm_16k,
                robot_tts_start_time=state.robot_tts_start_time,
            )
            self.osd_overlap_history.append(1 if overlap else 0)

            if (
                len(self.osd_overlap_history) >= OSD_HIT_WINDOW_SIZE
                and sum(self.osd_overlap_history) >= OSD_HITS_REQUIRED_IN_WINDOW
                and state.robot_is_speaking
                and state.robot_tts_start_time == token
            ):
                print("[OSD] Overlap detected - interrupting")
                self.trigger_barge()
        finally:
            next_audio = None
            next_token = 0.0
            with self.osd_lock:
                if (
                    self.osd_pending_audio is not None
                    and state.robot_is_speaking
                    and state.robot_tts_start_time == self.osd_pending_token
                ):
                    next_audio = self.osd_pending_audio
                    next_token = self.osd_pending_token
                    self.osd_pending_audio = None
                else:
                    self.osd_pending_audio = None
                    self.osd_inflight = False

            if next_audio is not None:
                self._start_osd_job(next_audio, next_token)

    def check_robot_user_overlap_fast(self):
        mic_bytes = b"".join(self.overlap_mic_buffer)
        mic = np.frombuffer(mic_bytes, dtype=np.int16).astype(np.float32)
        if mic.size < int(0.15 * SAMPLE_RATE):
            return False
        if state.robot_tts_pcm_16k is None:
            return False
        if time.time() - state.robot_tts_start_time < OVERLAP_CHECK_AFTER_ROBOT_START_S:
            return False

        template = state.robot_tts_pcm_16k.astype(np.float32)
        elapsed = time.time() - state.robot_tts_start_time
        start_idx = int(elapsed * SAMPLE_RATE)
        win_len = mic.shape[0]
        mic_rms = float(np.sqrt(np.mean(mic**2)) + 1e-9)

        lag_max = int((OVERLAP_LAG_OFFSETS_MS / 1000.0) * SAMPLE_RATE)
        step = int(0.01 * SAMPLE_RATE)
        lags = list(range(-lag_max, lag_max + 1, step))
        if 0 not in lags:
            lags.append(0)

        best_ratio = 0.0
        for lag in lags:
            t_start = start_idx + lag
            t_end = t_start + win_len
            if t_start < 0 or t_end > template.shape[0]:
                continue

            tmpl = template[t_start:t_end]
            denom = float(np.dot(tmpl, tmpl) + 1e-6)
            scale = float(np.dot(mic, tmpl) / denom)
            resid = mic - scale * tmpl
            resid_rms = float(np.sqrt(np.mean(resid**2)))
            ratio = resid_rms / mic_rms
            if ratio > best_ratio:
                best_ratio = ratio

        baseline_ready = len(self.overlap_best_ratio_history) >= OVERLAP_BASELINE_HISTORY_MIN
        baseline = float(np.median(self.overlap_best_ratio_history)) if baseline_ready else None
        self.overlap_best_ratio_history.append(best_ratio)

        if not baseline_ready:
            return False

        return best_ratio > OVERLAP_MIN_ABS_RESIDUAL_RATIO and best_ratio > (
            baseline + OVERLAP_BASELINE_DELTA
        )

    def trigger_barge(self):
        status = get_controller_status(timeout=0.2)
        self.captured_version = status.get("state_version", 0)

        state.current_version = self.captured_version
        state.is_user_talking = True

        try:
            interrupt_pepper(timeout=1)
            state.robot_is_speaking = False
            set_pepper_state("idle", timeout=1)
        except Exception as exception:
            print("Error changing state: {}".format(exception))

        self.triggered = True
        self.current_utterance_bytes = 0
        if not self.stt_transcriber.start_utterance(self.captured_version):
            self.triggered = False
            self.current_utterance_bytes = 0
            return

        for buffered_frame in self.ring_buffer:
            self.stt_transcriber.feed_audio(buffered_frame)
            self.current_utterance_bytes += len(buffered_frame)

        self.ring_buffer.clear()
        self.consecutive_speech = 0
        self._reset_overlap_tracking()

    def _reset_overlap_tracking(self):
        self.overlap_mic_buffer.clear()
        self.overlap_check_frames_accum = 0
        self.overlap_best_ratio_history.clear()
        self.osd_mic_buffer.clear()
        self.osd_check_frames_accum = 0
        self.osd_overlap_history.clear()
        with self.osd_lock:
            self.osd_pending_audio = None

    def reset_after_disconnect(self):
        self.debug_audio.flush(final=True)
        self.triggered = False
        self.buffer = b""
        self.current_utterance_bytes = 0
        self.stt_transcriber.cancel_last_utterance()
        self._reset_overlap_tracking()
