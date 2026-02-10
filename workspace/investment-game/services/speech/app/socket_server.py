import numpy as np
import threading
import socket
import time

from whisper import send_to_whisper
from speech import process_speech
from pepper import speak

HOST = "0.0.0.0"
PORT = 9700

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2

SILENCE_THRESHOLD = 300
SILENCE_DURATION = 1
MIN_SENTENCE_LEN = 1


def success_handler(text):
    response = process_speech(text)

    if response is not None:
        speak(response)


def start_sock_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind((HOST, PORT))
        sock.listen(1)
        print("Listening on {}:{}...".format(HOST, PORT))

        # Sorry Francisco...
        while True:
            conn, address = sock.accept()
            print("Connected to {}".format(address[0]))

            sentence_buffer = b""
            residual_buffer = b""
            silence_start_time = None
            is_speaking = False

            while True:
                data = conn.recv(12800)  # 4 channels
                if not data:
                    break

                combined_data = residual_buffer + data

                # each frame is 4 channels * 2 bytes = 8 bytes
                bytes_per_frame = 4 * SAMPLE_WIDTH
                length_to_process = (
                    len(combined_data) // bytes_per_frame
                ) * bytes_per_frame

                if length_to_process == 0:
                    residual_buffer = combined_data
                    continue

                process_now = combined_data[:length_to_process]
                residual_buffer = combined_data[length_to_process:]

                raw_data = np.frombuffer(process_now, dtype=np.int16)
                all_channels = raw_data.reshape(-1, 4)

                audio_data = all_channels[:, 0]
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))

                current_mono_bytes = audio_data.tobytes()

                if rms > SILENCE_THRESHOLD:
                    if not is_speaking:
                        print("Speech started...")

                    is_speaking = True
                    sentence_buffer += current_mono_bytes
                    silence_start_time = None
                elif is_speaking:
                    sentence_buffer += current_mono_bytes

                    if silence_start_time is None:
                        silence_start_time = time.time()

                    if time.time() - silence_start_time > SILENCE_DURATION:
                        if len(sentence_buffer) > (
                            SAMPLE_RATE * SAMPLE_WIDTH * MIN_SENTENCE_LEN
                        ):
                            threading.Thread(
                                target=send_to_whisper,
                                args=(
                                    sentence_buffer,
                                    SAMPLE_RATE,
                                    SAMPLE_WIDTH,
                                    success_handler,
                                ),
                            ).start()

                        sentence_buffer = b""
                        is_speaking = False
                        silence_start_time = None

            print("Lost connection")

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        sock.close()
