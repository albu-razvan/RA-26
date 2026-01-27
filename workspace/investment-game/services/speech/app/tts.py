# TODO: Migrate to gTTS since pyttsx3 2.7 cannot output
# to a file

import pyttsx3
import uuid
import os

AUDIO_DIR = "../audio"

engine = pyttsx3.init()

voices = engine.getProperty("voices")
for voice in voices:
    if "female" in voice.name.lower():
        engine.setProperty("voice", voice.id)
        break

engine.setProperty("rate", 150)


def to_speech(text):
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)

    filename = AUDIO_DIR + "/" + str(uuid.uuid4()).replace("-", "") + ".wav"
    full_path = os.path.abspath(filename)

    engine.save_to_file(text, filename)
    engine.runAndWait()

    return full_path
