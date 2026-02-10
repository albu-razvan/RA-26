import requests

CONTROLLER_API_URL = "http://controller:8000/handle-speech"


def process_speech(speech):
    try:
        response = requests.post(CONTROLLER_API_URL, json={"text": speech}, timeout=5)
        response.raise_for_status()

        data = response.json()
        if "text" in data and isinstance(data["text"], str):
            return data["text"]
        else:
            print(f"Unexpected response structure: {data}")

            return None

    except Exception as exception:
        print(exception)
