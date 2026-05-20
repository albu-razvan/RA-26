import requests

from . import llm
from . import algorithmic

from typing import Literal
from logger import log_conversation

SPEECH_API_URL = "http://speech:9701/speak"
SPEECH_INTERRUPT_URL = "http://speech:9701/interrupt"
PEPPER_ANIMATE_URL = "http://pepper:8080/animate"
PEPPER_STATE_URL = "http://pepper:8080/set-state"


def _set_pepper_state(state: Literal["processing", "idle"]):
    try:
        requests.post(PEPPER_STATE_URL, json={"state": state}, timeout=1)
    except Exception:
        pass


def stop_output():
    try:
        requests.post(SPEECH_INTERRUPT_URL, timeout=1)
    except Exception:
        pass

    _set_pepper_state("idle")


def _handle_movement(movement):
    if movement is not None:
        try:
            requests.post(PEPPER_ANIMATE_URL, json={"action": movement})
        except Exception as exception:
            print(str(exception))


def _get_start_game_response(condition):
    control_mode = "LLM-controlled" if condition == "LLM" else "Algorithmically controlled"

    return {
        "text": (
            "Hi there! I'm Pepper, an " + control_mode + " social robot from SoftBank Robotics. "
            "Welcome to the Investment Game! In this game, you make decisions about how much of the provided funds to invest. "
            "I will act as the broker: I decide how much of your invested amount to return to you. "
            "Each round, you choose an amount on the tablet, and I help by showing how your investments return over time. "
            "and I decide how much to return to your bank. Are you ready to start investing? Let's begin with round one now!"
        ),
        "movement": "open_arm",
    }


def handle_speech(input_text, game_state):
    if game_state.get("state") == "GAME_NOT_STARTED":
        return ""

    _set_pepper_state("processing")

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

    _set_pepper_state("idle")
    return response["text"]


def handle_game_event(event, game_state):
    _set_pepper_state("processing")

    player_id = game_state.get("player_id")
    condition = game_state.get("condition", "LLM")

    log_conversation(player_id, "Game Event", text=str(event))

    if event.get("state") == "GAME_STARTED":
        response = _get_start_game_response(condition)
    elif condition == "LLM":
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

    _set_pepper_state("idle")
