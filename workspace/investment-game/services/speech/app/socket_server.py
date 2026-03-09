import numpy as np
import threading
import socket
import collections
import requests
import webrtcvad
import noisereduce as nr

import state
from whisper import send_to_whisper
from speech import process_speech
from pepper import speak

HOST = "0.0.0.0"
PORT = 9700

CONTROLLER_URL = "http://controller:8000"
PEPPER_HANDLER_URL = "http://pepper:8080"

SAMPLE_RATE = 16000
# WebRTC VAD only accepts 10ms, 20ms or 30ms frames
FRAME_DURATION_MS = 20
FRAME_SIZE_BYTES = int(16000 * 0.02 * 2)


class AudioProcessor:
    def __init__(self):
        self.vad = webrtcvad.Vad(3)  # 0 to 3 for aggressiveness
        self.buffer = b""

        self.triggered = False
        self.voiced_frames = []
        self.ring_buffer = collections.deque(maxlen=20)

        self.silence_counter = 0
        self.SILENCE_LIMIT = 50  # ~1s of silence to end a sentence

        self.RMS_THRESHOLD = 500
        self.cooldown_frames = 0
        self.speech_start_threshold = 3
        self.consecutive_speech = 0

        self.captured_version = 0

    def get_rms(self, frame):
        data = np.frombuffer(frame, dtype=np.int16).astype(np.float32)

        return np.sqrt(np.mean(data**2))

    def process_stream(self, raw_chunk):
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

            rms_value = self.get_rms(frame)
            is_loud_enough = rms_value > self.RMS_THRESHOLD

            is_speech = self.vad.is_speech(frame, SAMPLE_RATE) and is_loud_enough

            if not self.triggered:
                self.ring_buffer.append(frame)

                if is_speech:
                    self.consecutive_speech += 1
                else:
                    self.consecutive_speech = 0

                if self.consecutive_speech >= self.speech_start_threshold:
                    print(f"[VAD] Voice detected")

                    try:
                        resp = requests.get(f"{CONTROLLER_URL}/status", timeout=0.5)
                        self.captured_version = resp.json().get("state_version", 0)
                    except Exception as exception:
                        print(f"Error fetching version: {exception}")
                        self.captured_version = 0

                    state.current_version = self.captured_version
                    state.is_user_talking = True

                    try:
                        requests.post(
                            f"{PEPPER_HANDLER_URL}/set-state",
                            json={"state": "listening"},
                            timeout=1,
                        )
                    except Exception as exception:
                        print(f"Error changing state: {exception}")

                    self.triggered = True
                    self.voiced_frames.extend(self.ring_buffer)
                    self.ring_buffer.clear()
                    self.consecutive_speech = 0
            else:
                self.voiced_frames.append(frame)

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

                    full_audio = b"".join(self.voiced_frames)
                    self.voiced_frames = []

                    if len(full_audio) < 8000:
                        return None

                    return self.clean_audio(full_audio), self.captured_version

        return None

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
        speak(response)


def start_sock_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    processor = AudioProcessor()

    try:
        sock.bind((HOST, PORT))
        sock.listen(1)
        print("Listening on {}:{}...".format(HOST, PORT))

        # Sorry Francisco...
        while True:
            connection, address = sock.accept()
            print("Connected to {}".format(address[0]))

            try:
                while True:
                    data = connection.recv(4096)
                    if not data:
                        break

                    result = processor.process_stream(data)
                    if result:
                        sentence, version = result

                        threading.Thread(
                            target=send_to_whisper,
                            args=(
                                sentence,
                                SAMPLE_RATE,
                                2,  # Sample width
                                success_handler,
                                version,
                            ),
                        ).start()
            except Exception as exception:
                print(f"Connection error: {exception}")
            finally:
                connection.close()
                print("Lost connection, waiting...")

                processor.triggered = False
                processor.voiced_frames = []
                processor.buffer = b""

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        sock.close()
