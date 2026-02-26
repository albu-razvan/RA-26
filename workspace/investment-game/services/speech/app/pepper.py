import socket
import state
import time
import os

PEPPER_IP = os.environ.get("ROBOT_IP", "192.168.0.100")
PEPPER_PORT = 6000

from tts import to_speech


def speak(text, version=None):
    if version is not None and version != state.current_version:
        print(f"Discarding speech (outdated before start): {text}")
        return

    if state.is_user_talking:
        print(f"User is talking. Queueing speech: '{text}'")

        while state.is_user_talking:
            if version is not None and version != state.current_version:
                print(
                    f"Discarding queued speech (version updated while waiting): {text}"
                )

                return

            time.sleep(0.1)

        print(f"Silence detected. Proceeding with queued speech: '{text}'")

    if version is not None and version != state.current_version:
        print(f"Discarding speech (outdated after waiting): {text}")

        return

    if text is None or text == "":
        return

    file = to_speech(text)
    _send_tts_to_pepper(file)

    try:
        os.remove(file)
    except Exception as exception:
        print("Could not delete temp file:", exception)


def _send_tts_to_pepper(sound_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((PEPPER_IP, PEPPER_PORT))

    file = open(sound_file, "rb")
    try:
        data = file.read(4096)
        while data:
            sock.send(data)
            data = file.read(4096)
    finally:
        file.close()

    sock.close()

    print("Sent TTS to Pepper: '{}'".format(sound_file))
