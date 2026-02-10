import requests
import uuid
import os

AUDIO_DIR = "../audio"
URL = "http://piper:5000"


def to_speech(text: str):
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)

    response = requests.post(URL, json={"text": text, "speaker": "prudence"})

    if response.status_code == 200:
        filename = f"{AUDIO_DIR}/{uuid.uuid4().hex}.wav"

        with open(filename, "wb") as f:
            f.write(response.content)

        return os.path.abspath(filename)
    else:
        print(f"Error: {response.status_code}")

        return None
