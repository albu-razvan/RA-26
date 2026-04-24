import requests
import wave
import io

CHANNELS = 1
PARAKEET_API_URL = "http://parakeet:9600/transcribe"


def send_to_parakeet(
    audio_bytes, sample_rate, sample_width, success_handler, state_version
):
    print("Sending {}s of audio to Parakeet...".format(len(audio_bytes) / 32000))

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
        res = requests.post(PARAKEET_API_URL, files=files)

        if res.status_code == 200:
            text = res.json().get("text", "").strip()

            if text:
                print("Recognized: {}".format(text))
                success_handler(text, state_version)
        else:
            print("Parakeet Error {}".format(res.status_code))

    except requests.exceptions.ConnectionError:
        print("Parakeet not available yet, waiting...")

        success_handler(
            """SYSTEM NOTE: The Parakeet model did not finish loading. 
Reply with a wake up message similar to (with some variation, make it playfull): 
\"Oh, it appears I am not quite able to understand what you are saying, give me some time to make sure everything is up and running!\"""",
            state_version,
        )

    except Exception as exception:
        print("Parakeet request failed: {}".format(exception))
    finally:
        if wave_file is not None:
            try:
                wave_file.close()
            except:
                pass
