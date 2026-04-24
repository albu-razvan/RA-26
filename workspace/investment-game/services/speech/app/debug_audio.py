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
                f"[DEBUG] Audio recording enabled: dir={self.output_dir}, chunk={chunk_seconds}s"
            )
        except Exception as e:
            print(f"[DEBUG] Could not create debug audio dir: {e}")
            self.enabled = False

    def _write_wav(self, pcm_bytes):
        if not self.enabled or not pcm_bytes:
            return

        ts_ms = int(time.time() * 1000)
        filename = f"mic_{ts_ms}_{self.file_index:06d}.wav"
        self.file_index += 1
        path = os.path.join(self.output_dir, filename)

        try:
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(pcm_bytes)
            print(f"[DEBUG] Wrote mic chunk: {path}")
        except Exception as e:
            print(f"[DEBUG] Failed to write mic chunk: {e}")

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
