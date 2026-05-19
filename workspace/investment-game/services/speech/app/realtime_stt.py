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

        self.recorder = AudioToTextRecorder(
            use_microphone=False,
            device="cpu",
            model=os.environ.get("STT_MODEL", "tiny.en"),
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

        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.recorder.text(self._handle_final_text)
            except Exception as exception:
                print(f"RealtimeSTT loop error: {exception}")

    def _handle_final_text(self, text):
        transcript = text.strip()
        if not transcript:
            return

        with self.lock:
            if self.pending_versions:
                state_version = self.pending_versions.popleft()
            else:
                state_version = 0

        print(f"Recognized: {transcript}")
        threading.Thread(
            target=self.success_handler,
            args=(transcript, state_version),
            daemon=True,
        ).start()

    def start_utterance(self, state_version):
        with self.lock:
            self.pending_versions.append(state_version)

    def cancel_last_utterance(self):
        with self.lock:
            if self.pending_versions:
                self.pending_versions.pop()

    def feed_audio(self, audio_bytes):
        try:
            self.recorder.feed_audio(audio_bytes, original_sample_rate=self.sample_rate)
        except Exception as exception:
            print(f"RealtimeSTT feed error: {exception}")

    def mark_utterance_end(self):
        trailing_silence = b"\x00\x00" * int(self.sample_rate * 0.45)
        self.feed_audio(trailing_silence)

    def shutdown(self):
        self.stop_event.set()
        try:
            self.recorder.shutdown()
        except Exception as exception:
            print(f"RealtimeSTT shutdown error: {exception}")
