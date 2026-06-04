import collections
import os
import threading
import time

from RealtimeSTT import AudioToTextRecorder


class RealtimeSpeechTranscriber:
    def __init__(self, sample_rate, success_handler):
        self.sample_rate = sample_rate
        self.success_handler = success_handler

        self.pending_versions = collections.deque()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.awaiting_final_text = False
        self.finalization_token = 0
        self.block_new_until = 0.0
        self.finalization_timeout_s = float(
            os.environ.get("STT_FINALIZATION_TIMEOUT_SECONDS", "3.5")
        )
        self.finalization_grace_s = float(
            os.environ.get("STT_FINALIZATION_GRACE_SECONDS", "2.0")
        )
        self.recovery_cooldown_s = float(
            os.environ.get("STT_RECOVERY_COOLDOWN_SECONDS", "0.6")
        )
        self.reset_on_finalization_timeout = (
            os.environ.get("STT_RESET_ON_FINALIZATION_TIMEOUT", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )

        self.recorder = self._build_recorder()

        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def _build_recorder(self):
        return AudioToTextRecorder(
            use_microphone=False,
            device="cpu",
            model=os.environ.get("STT_MODEL", "base.en"),
            language="en",
            spinner=False,
            no_log_file=True,
            compute_type="int8",
            beam_size=1,
            post_speech_silence_duration=0.25,
            early_transcription_on_silence=120,
            min_length_of_recording=0.2,
            enable_realtime_transcription=False,
            ensure_sentence_ends_with_period=False,
        )

    def _reset_recorder(self):
        try:
            self.recorder.shutdown()
        except Exception as exception:
            print("RealtimeSTT reset shutdown error: {}".format(exception))

        self.recorder = self._build_recorder()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.recorder.text(self._handle_final_text)
            except Exception as exception:
                print("RealtimeSTT loop error: {}".format(exception))

    def _handle_final_text(self, text):
        transcript = (text or "").strip()
        with self.lock:
            if self.pending_versions:
                state_version = self.pending_versions.popleft()
            else:
                self.awaiting_final_text = False
                self.finalization_token += 1
                if transcript:
                    print(
                        "Recognized transcript without matching utterance. "
                        "Dropping stale STT output."
                    )

                return

            self.awaiting_final_text = False
            self.finalization_token += 1

        if not transcript:
            print("Recognized empty transcript. Dropping utterance.")
            return

        print("Recognized: {}".format(transcript))
        threading.Thread(
            target=self.success_handler,
            args=(transcript, state_version),
            daemon=True,
        ).start()

    def start_utterance(self, state_version):
        with self.lock:
            if time.time() < self.block_new_until:
                return False

            if self.awaiting_final_text:
                return False

            self.pending_versions.append(state_version)

            return True

    def cancel_last_utterance(self):
        with self.lock:
            if self.pending_versions:
                self.pending_versions.pop()

            self.awaiting_final_text = False
            self.finalization_token += 1

    def is_ready_for_new_utterance(self):
        with self.lock:
            return not self.awaiting_final_text

    def _finalization_watchdog(self, token):
        self.stop_event.wait(self.finalization_timeout_s)

        if self.stop_event.is_set():
            return

        with self.lock:
            if not self.awaiting_final_text or token != self.finalization_token:
                return

        print(
            "RealtimeSTT finalization timeout. Waiting grace period of {}s.".format(
                self.finalization_grace_s
            )
        )
        trailing_silence = b"\x00\x00" * int(self.sample_rate * 1.0)
        self.feed_audio(trailing_silence)

        self.stop_event.wait(self.finalization_grace_s)
        if self.stop_event.is_set():
            return

        with self.lock:
            if not self.awaiting_final_text or token != self.finalization_token:
                return

            self.awaiting_final_text = False
            if self.pending_versions:
                self.pending_versions.popleft()
            self.finalization_token += 1
            self.block_new_until = time.time() + self.recovery_cooldown_s

        print("RealtimeSTT finalization timed out after grace. Dropping utterance.")
        if self.reset_on_finalization_timeout:
            print("RealtimeSTT reset enabled after finalization timeout.")
            self._reset_recorder()

    def feed_audio(self, audio_bytes):
        try:
            self.recorder.feed_audio(audio_bytes, original_sample_rate=self.sample_rate)
        except Exception as exception:
            print("RealtimeSTT feed error: {}".format(exception))

    def mark_utterance_end(self):
        with self.lock:
            if not self.pending_versions:
                return

            self.awaiting_final_text = True
            self.finalization_token += 1
            token = self.finalization_token

        trailing_silence = b"\x00\x00" * int(self.sample_rate * 0.8)
        self.feed_audio(trailing_silence)

        threading.Thread(target=self._finalization_watchdog, args=(token,), daemon=True).start()

    def shutdown(self):
        self.stop_event.set()
        try:
            self.recorder.shutdown()
        except Exception as exception:
            print("RealtimeSTT shutdown error: {}".format(exception))
