import collections
import os
import threading

from RealtimeSTT import AudioToTextRecorder


class RealtimeSpeechTranscriber:
    def __init__(self, sample_rate, success_handler):
        self.sample_rate = sample_rate
        self.success_handler = success_handler

        self.pending_versions = collections.deque()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.awaiting_final_text = False
        self.finalization_timeout_s = 1.2

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
                if transcript:
                    print(
                        "Recognized transcript without matching utterance. "
                        "Dropping stale STT output."
                    )

                return

            self.awaiting_final_text = False

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
            if self.awaiting_final_text:
                return False

            self.pending_versions.append(state_version)

            return True

    def cancel_last_utterance(self):
        with self.lock:
            if self.pending_versions:
                self.pending_versions.pop()

            self.awaiting_final_text = False

    def is_ready_for_new_utterance(self):
        with self.lock:
            return not self.awaiting_final_text

    def _finalization_watchdog(self):
        self.stop_event.wait(self.finalization_timeout_s)

        if self.stop_event.is_set():
            return

        with self.lock:
            if not self.awaiting_final_text:
                return

            self.awaiting_final_text = False
            if self.pending_versions:
                self.pending_versions.popleft()

        print("RealtimeSTT finalization timeout. Resetting STT stream.")
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

        trailing_silence = b"\x00\x00" * int(self.sample_rate * 0.8)
        self.feed_audio(trailing_silence)

        threading.Thread(target=self._finalization_watchdog, daemon=True).start()

    def shutdown(self):
        self.stop_event.set()
        try:
            self.recorder.shutdown()
        except Exception as exception:
            print("RealtimeSTT shutdown error: {}".format(exception))
