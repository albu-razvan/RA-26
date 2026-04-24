import socket
import state
import time
import os
import wave
import numpy as np

PEPPER_IP = os.environ.get("ROBOT_IP", "192.168.0.100")
PEPPER_PORT = 6000

from tts import to_speech


def get_wav_duration(filename):
    try:
        with wave.open(filename, 'r') as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except Exception as e:
        print(f"Error getting wav duration: {e}")
        return 0.0


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
    if not file:
        return

    # Cache the PCM template so the mic server can quickly detect overlap
    # (robot talking + user speaking) without waiting for diarization.
    try:
        with wave.open(file, "rb") as f:
            sr_before = f.getframerate()
            nframes = f.getnframes()
            raw = f.readframes(nframes)

            # Expect 16-bit PCM; if not, the WAV is probably unsuitable.
            audio = np.frombuffer(raw, dtype=np.int16)
            if f.getnchannels() > 1:
                audio = audio.reshape(-1, f.getnchannels())[:, 0]

            sr = sr_before
            if sr_before != 16000:
                # Simple linear resample to 16k for the mic pipeline.
                x_old = np.linspace(0.0, 1.0, num=audio.shape[0], endpoint=False)
                x_new = np.linspace(0.0, 1.0, num=int(audio.shape[0] * 16000 / sr_before), endpoint=False)
                audio_f = audio.astype(np.float32)
                audio_rs = np.interp(x_new, x_old, audio_f).astype(np.int16)
                audio = audio_rs
                sr = 16000

            state.robot_tts_pcm_16k = audio
            state.robot_tts_start_time = time.time()
    except Exception as e:
        print(f"Could not cache TTS template for overlap detection: {e}")

    duration = get_wav_duration(file)
    
    # We add 0.5s to the duration to account for transmission time + Pepper's buffer
    state.robot_speak_end_time = time.time() + duration + 0.5

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
