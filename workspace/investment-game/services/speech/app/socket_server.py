import numpy as np
import threading
import socket
import collections
import requests
import webrtcvad
import noisereduce as nr
import os
import time
import state

from speech import (
    process_speech,
    DEBUG_AUDIO_RECORD,
    DEBUG_AUDIO_RECORD_DIR,
    DEBUG_AUDIO_RECORD_CHUNK_SECONDS,
)
from pepper import speak
from debug_audio import DebugAudioRecorder
from osd_detector import OSDDetector
from realtime_stt import RealtimeSpeechTranscriber

HOST = "0.0.0.0"
PORT_MIC = 9702

CONTROLLER_URL = "http://controller:8000"
PEPPER_HANDLER_URL = "http://pepper:8080"

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 20
FRAME_SIZE_BYTES = int(16000 * 0.02 * 2 * 1)  # 1 channel

# Overlapped-speech detection
OSD_WINDOW_MS = 1000  # Audio window passed to OSD model; larger is steadier, smaller is faster
OSD_CHECK_INTERVAL_MS = 100  # How often to run OSD checks while robot speaks
OSD_WINDOW_FRAMES = OSD_WINDOW_MS // FRAME_DURATION_MS
OSD_CHECK_INTERVAL_FRAMES = OSD_CHECK_INTERVAL_MS // FRAME_DURATION_MS
OSD_MIN_AUDIO_MS = 100  # Minimum buffered mic audio before running OSD (avoid tiny/noisy checks)
OSD_MIN_AUDIO_SAMPLES = int((OSD_MIN_AUDIO_MS / 1000.0) * SAMPLE_RATE)
OSD_RESIDUAL_BOOST = 4.5  # Boost factor for residual energy in OSD overlap scoring
OSD_MAX_GAIN = 60.0  # Upper cap for residual amplification in OSD path.
OSD_TEMPLATE_LAG_STEP_MS = 20  # Step size when scanning lag offsets for robot-template alignment
OSD_USE_DENOISE = True  # If True, denoise mic audio before OSD (more CPU, can reduce false hits)
OVERLAP_CHECK_WINDOW_MS = 600  # Fast overlap detector mic window (template-matching path)
OVERLAP_CHECK_INTERVAL_MS = 60  # How often fast overlap checks run during robot speech.
OVERLAP_CHECK_WINDOW_FRAMES = OVERLAP_CHECK_WINDOW_MS // FRAME_DURATION_MS
OVERLAP_CHECK_INTERVAL_FRAMES = OVERLAP_CHECK_INTERVAL_MS // FRAME_DURATION_MS
OVERLAP_MIN_ABS_RESIDUAL_RATIO = 0.09  # Absolute residual floor before considering user overlap
OVERLAP_LAG_OFFSETS_MS = 350  # +/- lag search range around expected robot playback alignment
OVERLAP_BASELINE_DELTA = 0.02  # Required jump above recent robot-only baseline to trigger barge-in
OVERLAP_BASELINE_HISTORY_MIN = 2  # Minimum robot-only history windows before baseline-based triggering
OVERLAP_CHECK_AFTER_ROBOT_START_S = 0.1  # Delay checks briefly after TTS start to avoid startup transients


class AudioProcessor:
    def __init__(self, osd_detector, stt_transcriber):
        self.vad = webrtcvad.Vad(3)
        self.buffer = b""
        self.osd_detector = osd_detector
        self.stt_transcriber = stt_transcriber

        self.triggered = False
        self.voiced_frames = []
        self.ring_buffer = collections.deque(maxlen=20)

        self.silence_counter = 0
        self.SILENCE_LIMIT = int(os.environ.get("SILENCE_LIMIT_FRAMES", "70"))

        self.RMS_THRESHOLD = 500
        self.cooldown_frames = 0
        self.speech_start_threshold = 4
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

        self.captured_version = 0

        self.debug_audio = DebugAudioRecorder(
            enabled=DEBUG_AUDIO_RECORD,
            output_dir=DEBUG_AUDIO_RECORD_DIR,
            chunk_seconds=DEBUG_AUDIO_RECORD_CHUNK_SECONDS,
            sample_rate=SAMPLE_RATE,
        )

    def _start_osd_job(self, audio_i16: np.ndarray, token: float):
        threading.Thread(
            target=self._run_osd_job,
            args=(audio_i16, token),
            daemon=True,
        ).start()

    def _run_osd_job(self, audio_i16: np.ndarray, token: float):
        try:
            if time.time() >= state.robot_speak_end_time:
                return
            if state.robot_tts_start_time != token:
                return

            if self.osd_detector is None:
                return

            overlap = self.osd_detector.detect_overlap(
                audio_i16,
                robot_template_i16=state.robot_tts_pcm_16k,
                robot_tts_start_time=state.robot_tts_start_time,
            )
            if (
                overlap
                and time.time() < state.robot_speak_end_time
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
                    and time.time() < state.robot_speak_end_time
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

            try:
                data_np = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
                front = data_np
                front_int16 = front.astype(np.int16).tobytes()

                rms_front = np.sqrt(np.mean(front.astype(np.float32)**2))
                
                is_robot_speaking = time.time() < state.robot_speak_end_time

                is_vad_speech = self.vad.is_speech(front_int16, SAMPLE_RATE)
                is_loud_enough = rms_front > self.RMS_THRESHOLD
                is_speech = is_vad_speech and is_loud_enough

                if is_robot_speaking:
                    # reset overlap baseline/history so we
                    # don't compare against a previous TTS message.
                    if state.robot_tts_start_time != self.last_robot_tts_start_time:
                        self.last_robot_tts_start_time = state.robot_tts_start_time
                        self.overlap_mic_buffer.clear()
                        self.overlap_check_frames_accum = 0
                        self.overlap_best_ratio_history.clear()
                        self.osd_mic_buffer.clear()
                        self.osd_check_frames_accum = 0

                        with self.osd_lock:
                            self.osd_pending_audio = None

                    # Collect mic audio while robot is speaking so we can
                    # quickly detect overlap using the cached TTS template.
                    self.overlap_mic_buffer.append(front_int16)
                    self.overlap_check_frames_accum += 1

                    if self.overlap_check_frames_accum >= OVERLAP_CHECK_INTERVAL_FRAMES:
                        self.overlap_check_frames_accum = 0
                        if state.robot_tts_pcm_16k is not None:
                            overlap_hit = self.check_robot_user_overlap_fast()
                            if overlap_hit and (is_vad_speech or rms_front > (self.RMS_THRESHOLD * 0.25)):
                                print("[OVERLAP] Detected user overlap - interrupting")
                                self.trigger_barge()

                    # OSD-based barge-in (model detects true overlapping speech)
                    self.osd_mic_buffer.append(front_int16)
                    self.osd_check_frames_accum += 1
                    if (
                        len(self.osd_mic_buffer) > 0
                        and self.osd_check_frames_accum >= OSD_CHECK_INTERVAL_FRAMES
                    ):
                        self.osd_check_frames_accum = 0
                        token = state.robot_tts_start_time
                        audio_i16 = np.frombuffer(
                            b"".join(list(self.osd_mic_buffer)),
                            dtype=np.int16,
                        )

                        if audio_i16.size < OSD_MIN_AUDIO_SAMPLES:
                            continue

                        with self.osd_lock:
                            if self.osd_inflight:
                                # Keep only the freshest buffer while a check is
                                # running so we do not queue stale windows.
                                self.osd_pending_audio = audio_i16
                                self.osd_pending_token = token
                            else:
                                self.osd_inflight = True
                                self.osd_pending_audio = None
                                self._start_osd_job(audio_i16, token)

                else:
                    self.overlap_mic_buffer.clear()
                    self.overlap_check_frames_accum = 0
                    self.osd_mic_buffer.clear()
                    self.osd_check_frames_accum = 0
                    with self.osd_lock:
                        self.osd_pending_audio = None

                if not self.triggered:
                    self.ring_buffer.append(front_int16)

                    if is_speech:
                        self.consecutive_speech += 1
                    else:
                        self.consecutive_speech = 0

                    if self.consecutive_speech >= self.speech_start_threshold and not is_robot_speaking:
                        print("[VAD] Voice detected")

                        try:
                            resp = requests.get(f"{CONTROLLER_URL}/status", timeout=0.2)
                            self.captured_version = resp.json().get("state_version", 0)
                        except Exception as exception:
                            print(f"Error fetching version: {exception}")
                            self.captured_version = 0

                        state.current_version = self.captured_version
                        state.is_user_talking = True

                        try:
                            requests.post(
                                f"{PEPPER_HANDLER_URL}/interrupt",
                                timeout=1,
                            )
                            state.robot_speak_end_time = 0.0
                            requests.post(
                                f"{PEPPER_HANDLER_URL}/set-state",
                                json={"state": "listening"},
                                timeout=1,
                            )
                        except Exception as exception:
                            print(f"Error changing state: {exception}")

                        self.triggered = True
                        self.current_utterance_bytes = 0
                        self.stt_transcriber.start_utterance(self.captured_version)
                        for buffered_frame in self.ring_buffer:
                            self.stt_transcriber.feed_audio(buffered_frame)
                            self.current_utterance_bytes += len(buffered_frame)
                        self.ring_buffer.clear()
                        self.consecutive_speech = 0
                else:
                    self.stt_transcriber.feed_audio(front_int16)
                    self.current_utterance_bytes += len(front_int16)

                    if not is_speech:
                        self.silence_counter += 1
                    else:
                        self.silence_counter = 0

                    if self.silence_counter > self.SILENCE_LIMIT:
                        print("[VAD] Processing audio chunk...")

                        state.is_user_talking = False

                        try:
                            requests.post(
                                f"{PEPPER_HANDLER_URL}/set-state",
                                json={"state": "processing"},
                                timeout=1,
                            )
                        except Exception as exception:
                            print(f"Error changing state: {exception}")

                        self.triggered = False
                        self.silence_counter = 0

                        if self.current_utterance_bytes < 8000:
                            self.stt_transcriber.cancel_last_utterance()
                            self.current_utterance_bytes = 0
                            return None

                        self.stt_transcriber.mark_utterance_end()
                        self.current_utterance_bytes = 0
            except Exception as e:
                print(f"Frame processing error: {e}")
                continue

        return None

    def check_robot_user_overlap_fast(self):
        """Fast overlap detection using the cached robot TTS template.

        If the mic window cannot be explained well by the expected robot
        playback, we assume the user is speaking over the robot.
        """

        # Build mic window (int16 -> float32)
        mic_bytes = b"".join(self.overlap_mic_buffer)
        mic = np.frombuffer(mic_bytes, dtype=np.int16).astype(np.float32)
        if mic.size < int(0.15 * SAMPLE_RATE):
            return False

        if state.robot_tts_pcm_16k is None:
            return False

        # Give the audio path a moment to settle so we don't match against
        # the wrong part of the template.
        if time.time() - state.robot_tts_start_time < OVERLAP_CHECK_AFTER_ROBOT_START_S:
            return False

        template = state.robot_tts_pcm_16k.astype(np.float32)

        elapsed = time.time() - state.robot_tts_start_time
        start_idx = int(elapsed * SAMPLE_RATE)
        win_len = mic.shape[0]

        mic_rms = float(np.sqrt(np.mean(mic**2)) + 1e-9)

        lag_max = int((OVERLAP_LAG_OFFSETS_MS / 1000.0) * SAMPLE_RATE)
        step = int(0.01 * SAMPLE_RATE)  # 10ms step
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

        # Update history after computing baseline.
        self.overlap_best_ratio_history.append(best_ratio)

        if not baseline_ready:
            return False

        # Trigger only if residual jumped meaningfully compared to recent
        # robot-only behavior.
        return best_ratio > OVERLAP_MIN_ABS_RESIDUAL_RATIO and best_ratio > (baseline + OVERLAP_BASELINE_DELTA)

    def trigger_barge(self):
        try:
            resp = requests.get(f"{CONTROLLER_URL}/status", timeout=0.2)
            self.captured_version = resp.json().get("state_version", 0)
        except Exception:
            self.captured_version = 0

        state.current_version = self.captured_version
        state.is_user_talking = True

        try:
            requests.post(f"{PEPPER_HANDLER_URL}/interrupt", timeout=1)
            state.robot_speak_end_time = 0.0
            requests.post(
                f"{PEPPER_HANDLER_URL}/set-state",
                json={"state": "listening"},
                timeout=1,
            )
        except Exception as e:
            print(f"Error triggering barge: {e}")

        self.triggered = True
        self.current_utterance_bytes = 0
        self.stt_transcriber.start_utterance(self.captured_version)
        for buffered_frame in self.ring_buffer:
            self.stt_transcriber.feed_audio(buffered_frame)
            self.current_utterance_bytes += len(buffered_frame)
        self.voiced_frames = []
        self.ring_buffer.clear()
        self.consecutive_speech = 0
        self.overlap_mic_buffer.clear()
        self.overlap_check_frames_accum = 0
        self.overlap_best_ratio_history.clear()
        self.osd_mic_buffer.clear()
        self.osd_check_frames_accum = 0
        with self.osd_lock:
            self.osd_pending_audio = None

    def clean_audio(self, audio_bytes):
        try:
            data_np = np.frombuffer(audio_bytes, dtype=np.int16)

            if len(data_np) < 4000:
                return audio_bytes

            reduced_noise = nr.reduce_noise(
                y=data_np, sr=SAMPLE_RATE, stationary=True, prop_decrease=0.75
            )

            return reduced_noise.tobytes()
        except Exception as exception:
            print("Noise reduction failed:", exception)
            return audio_bytes


def success_handler(text, state_version):
    response = process_speech(text, state_version)

    if response is not None:
        try:
            status_response = requests.get(f"{CONTROLLER_URL}/status", timeout=1)
            if status_response.json().get("state_version", 0) != state_version:
                print("Game state changed while generating speech. Dropping response.")
                return
        except Exception as exception:
            print(f"Status check failed: {exception}")

        speak(response, version=state_version)


class MicServer:
    def __init__(self, audio_processor):
        self.processor = audio_processor

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, PORT_MIC))
        sock.listen(1)
        print(f"[MIC] Listening on {HOST}:{PORT_MIC}")

        while True:
            conn, addr = sock.accept()
            print(f"[MIC] Connected from {addr}")
            self._handle(conn)

    def _handle(self, conn):
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break

                self.processor.process_stream(data)
        except Exception as e:
            print(f"[MIC] Connection error: {e}")
        finally:
            self.processor.debug_audio.flush(final=True)
            conn.close()

            print("[MIC] Connection closed")

            self.processor.triggered = False
            self.processor.voiced_frames = []
            self.processor.buffer = b""
            self.processor.current_utterance_bytes = 0
            self.processor.stt_transcriber.cancel_last_utterance()
            self.processor.overlap_mic_buffer.clear()
            self.processor.overlap_check_frames_accum = 0
            self.processor.overlap_best_ratio_history.clear()
            self.processor.osd_mic_buffer.clear()
            self.processor.osd_check_frames_accum = 0
            
            with self.processor.osd_lock:
                self.processor.osd_pending_audio = None


def start_sock_server():
    stt_transcriber = RealtimeSpeechTranscriber(
        sample_rate=SAMPLE_RATE,
        success_handler=success_handler,
    )

    osd_detector = None
    try:
        osd_detector = OSDDetector(
            hf_token=os.environ.get("HF_TOKEN"),
            sample_rate=SAMPLE_RATE,
            lag_offsets_ms=OVERLAP_LAG_OFFSETS_MS,
            residual_boost=OSD_RESIDUAL_BOOST,
            max_gain=OSD_MAX_GAIN,
            lag_step_ms=OSD_TEMPLATE_LAG_STEP_MS,
            use_denoise=OSD_USE_DENOISE,
        )
    except Exception as e:
        print(f"[OSD] Failed to load pipeline: {e}")

    processor = AudioProcessor(osd_detector, stt_transcriber)
    mic_server = MicServer(processor)

    threading.Thread(target=mic_server.start, daemon=True).start()

    print("[MAIN] Mic server started")
    while True:
        threading.Event().wait()
