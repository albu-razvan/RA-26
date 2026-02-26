import requests

from . import llm
from . import algorithmic

SPEECH_API_URL = "http://speech:9701/speak"
PEPPER_API_URL = "http://pepper:8080/animate"


def _handle_movement(movement):
    if movement is not None:
        try:
            requests.post(PEPPER_API_URL, json={"action": movement})
        except Exception as exception:
            print(str(exception))


def handle_speech(input_text, game_state):
    condition = game_state.get("condition", "LLM")

    if condition == "LLM":
        response = llm.handle_speech(input_text, game_state)
    else:
        response = algorithmic.handle_speech(input_text)

    _handle_movement(response["movement"])

    return response["text"]


def handle_game_event(event, game_state):
    condition = game_state.get("condition", "LLM")

    if condition == "LLM":
        response = llm.handle_game_event(event, game_state)
    else:
        response = algorithmic.handle_game_event(event, game_state)

    _handle_movement(response["movement"])

    try:
        requests.post(
            SPEECH_API_URL,
            json={
                "text": response.get("text", ""),
                "state_version": game_state["state_version"],
            },
            timeout=5,
        )
    except Exception as exception:
        print(str(exception))
