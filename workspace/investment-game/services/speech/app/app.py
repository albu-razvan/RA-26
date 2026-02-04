import numpy as np
import threading
import socket
import time
import sys
import os

from whisper import send_to_whisper
from pepper import send_tts_to_pepper
from tts import to_speech

sys.stdout.reconfigure(line_buffering=True)

HOST = "0.0.0.0"
PORT = 9700

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2

SILENCE_THRESHOLD = 500
SILENCE_DURATION = 2.0
MIN_SENTENCE_LEN = 1


def success_handler(text):
    file = to_speech(text)
    send_tts_to_pepper(file)

    try:
        os.remove(file)
    except Exception as exception:
        print("Could not delete temp file:", exception)


def main():
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
                data = conn.recv(12800)  # Increased buffer size for 4 channels
                if not data:
                    break

                combined_data = residual_buffer + data

                # 2. Calculate how many bytes constitute complete 4-channel frames
                # Each frame is 4 channels * 2 bytes = 8 bytes
                bytes_per_frame = 4 * SAMPLE_WIDTH
                length_to_process = (
                    len(combined_data) // bytes_per_frame
                ) * bytes_per_frame

                if length_to_process == 0:
                    residual_buffer = combined_data
                    continue

                # Split processing data from leftovers
                process_now = combined_data[:length_to_process]
                residual_buffer = combined_data[length_to_process:]

                # 3. Convert to numpy and Reshape safely
                raw_data = np.frombuffer(process_now, dtype=np.int16)
                all_channels = raw_data.reshape(-1, 4)

                # 4. Extract Mic 0 (Front) for your RMS and Whisper
                audio_data = all_channels[:, 0]
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))

                # Use the extracted mono channel for your logic
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


if __name__ == "__main__":
    main()
