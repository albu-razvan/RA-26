import requests
import os

CONTROLLER_API_URL = "http://controller:8000/handle-speech"


def _env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEBUG_AUDIO_RECORD = _env_flag("DEBUG_AUDIO_RECORD", default=False)
DEBUG_AUDIO_RECORD_DIR = os.environ.get("DEBUG_AUDIO_RECORD_DIR", "/tmp/audio_debug")
DEBUG_AUDIO_RECORD_CHUNK_SECONDS = float(
    os.environ.get("DEBUG_AUDIO_RECORD_CHUNK_SECONDS", "10")
)


def process_speech(speech, state_version):
    try:
        response = requests.post(
            CONTROLLER_API_URL,
            json={"text": speech, "state_version": state_version},
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        if "text" in data and isinstance(data["text"], str):
            return data["text"]
        else:
            print(f"Unexpected response structure: {data}")

            return None

    except Exception as exception:
        print(exception)
