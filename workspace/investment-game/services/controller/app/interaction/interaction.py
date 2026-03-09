import requests

from . import llm
from . import algorithmic

from logger import log_conversation

SPEECH_API_URL = "http://speech:9701/speak"
PEPPER_API_URL = "http://pepper:8080/animate"


def _handle_movement(movement):
    if movement is not None:
        try:
            requests.post(PEPPER_API_URL, json={"action": movement})
        except Exception as exception:
            print(str(exception))


def handle_speech(input_text, game_state):
    player_id = game_state.get("player_id")
    condition = game_state.get("condition", "LLM")

    log_conversation(player_id, "Human (Speech)", text=input_text)

    if condition == "LLM":
        response = llm.handle_speech(input_text, game_state)
    else:
        response = algorithmic.handle_speech(input_text)

    log_conversation(
        player_id,
        f"Pepper (${condition})",
        text=response.get("text"),
        movement=response.get("movement"),
    )

    _handle_movement(response["movement"])

    return response["text"]


def handle_game_event(event, game_state):
    player_id = game_state.get("player_id")
    condition = game_state.get("condition", "LLM")

    log_conversation(player_id, "Game Event", text=str(event))

    if condition == "LLM":
        response = llm.handle_game_event(event, game_state)
    else:
        response = algorithmic.handle_game_event(event, game_state)

    log_conversation(
        player_id,
        f"Pepper (${condition})",
        text=response.get("text"),
        movement=response.get("movement"),
    )

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
