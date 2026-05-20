import os
import time
import wave


class DebugAudioRecorder:
    def __init__(self, enabled, output_dir, chunk_seconds, sample_rate):
        self.enabled = enabled
        self.output_dir = output_dir
        self.chunk_bytes = max(1, int(chunk_seconds * sample_rate * 2))
        self.buffer = bytearray()
        self.file_index = 0
        self.sample_rate = sample_rate

        if not self.enabled:
            return

        try:
            os.makedirs(self.output_dir, exist_ok=True)
            print(
                "[DEBUG] Audio recording enabled: dir={}, chunk={}s".format(
                    self.output_dir,
                    chunk_seconds,
                )
            )
        except Exception as exception:
            print("[DEBUG] Could not create debug audio dir: {}".format(exception))
            self.enabled = False

    def _write_wav(self, pcm_bytes):
        if not self.enabled or not pcm_bytes:
            return

        ts_ms = int(time.time() * 1000)
        filename = "mic_{}_{:06d}.wav".format(ts_ms, self.file_index)
        self.file_index += 1
        path = os.path.join(self.output_dir, filename)

        try:
            with wave.open(path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(pcm_bytes)
            print("[DEBUG] Wrote mic chunk: {}".format(path))
        except Exception as exception:
            print("[DEBUG] Failed to write mic chunk: {}".format(exception))

    def append(self, raw_chunk):
        if not self.enabled or not raw_chunk:
            return

        self.buffer.extend(raw_chunk)
        self.flush(final=False)

    def flush(self, final=False):
        if not self.enabled:
            return

        while len(self.buffer) >= self.chunk_bytes:
            chunk = bytes(self.buffer[: self.chunk_bytes])
            del self.buffer[: self.chunk_bytes]
            self._write_wav(chunk)

        if final and len(self.buffer) > 0:
            chunk = bytes(self.buffer)
            self.buffer.clear()
            self._write_wav(chunk)
