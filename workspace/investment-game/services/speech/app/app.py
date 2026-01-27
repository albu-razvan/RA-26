import numpy as np
import threading
import socket
import time
import os

from whisper import send_to_whisper
from pepper import send_tts_to_pepper
from tts import to_speech

HOST = "0.0.0.0"
PORT = 9700

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2

SILENCE_THRESHOLD = 500
SILENCE_DURATION = 1.0
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

        conn, address = sock.accept()
        print("Connected to {}".format(address[0]))

        sentence_buffer = b""
        silence_start_time = None
        is_speaking = False

        # Sorry Francisco
        while True:
            data = conn.recv(3200)
            if not data:
                break

            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))

            if rms > SILENCE_THRESHOLD:
                if not is_speaking:
                    print("Speech started...")

                is_speaking = True
                sentence_buffer += data
                silence_start_time = None
            else:
                if is_speaking:
                    sentence_buffer += data

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

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
