import requests
import wave
import io

CHANNELS = 1
WHISPER_API_URL = "http://whisper:9600/transcribe"


def send_to_whisper(audio_bytes, sample_rate, sample_width, success_handler):
    print("Sending {}s of audio to Whisper...".format(len(audio_bytes) / 32000))

    wave_file = None
    try:
        buffer = io.BytesIO()

        wave_file = wave.open(buffer, "wb")
        wave_file.setnchannels(CHANNELS)
        wave_file.setsampwidth(sample_width)
        wave_file.setframerate(sample_rate)
        wave_file.writeframes(audio_bytes)
        wave_file.close()

        buffer.seek(0)

        files = {"file": ("audio.wav", buffer, "audio/wav")}
        res = requests.post(WHISPER_API_URL, files=files, timeout=5)

        if res.status_code == 200:
            text = res.json().get("text", "").strip()

            if text:
                print("Recognized: {}".format(text))
                success_handler(text)
        else:
            print("Whisper Error {}".format(res.status_code))

    except Exception as exception:
        print("Whisper request failed: {}".format(exception))
    finally:
        if wave_file is not None:
            try:
                wave_file.close()
            except:
                pass
