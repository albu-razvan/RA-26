import os
import time
import requests

from . import llm
from . import algorithmic

from typing import Literal
from logger import log_conversation

ALG_ACCEPT_SPEECH = os.getenv("ALG_ACCEPT_SPEECH", "false").lower() in ("true", "1", "yes")

SPEECH_API_URL = "http://speech:9701/speak"
SPEECH_INTERRUPT_URL = "http://speech:9701/interrupt"
PEPPER_ANIMATE_URL = "http://pepper:8080/animate"
PEPPER_STATE_URL = "http://pepper:8080/set-state"


def _set_pepper_state(state: Literal["processing", "idle", "speaking", "listening"]):
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
    if condition in {"LLM", "SEL-LLM"}:
        control_mode = "an LLM-controlled"
    elif condition in {"ALG", "SEL-ALG"}:
        control_mode = "a pre scripted"
    else:
        control_mode = "a"

    return {
        "text": (
            "Hi there! I'm Pepper, " + control_mode + " social robot from SoftBank Robotics. "
            "Welcome to the Investment Game! In this game, you decide how much of the provided funds to invest during each round. "
            "I will receive three times what you invest, and I will decide how much of this invested amount to return to you. "
            "Are you ready to start investing? Let's begin with round one now!"
        ),
        "movement": "open_arm",
    }


def handle_speech(input_text, game_state):
    if game_state.get("state") != "GAME_ONGOING":
        return ""

    player_id = game_state.get("player_id")
    condition = game_state.get("condition", "LLM")
    game_number = game_state.get("current_game_number")

    _set_pepper_state("processing")

    if condition == "ALG" and not ALG_ACCEPT_SPEECH:
        # artificial delay to match other condition processing time
        time.sleep(0.75)
        
        response = {
            "text": "Sorry, I don't have an answer, let's keep playing.",
            "movement": "open_arm",
        }
        log_conversation(
            player_id,
            f"Pepper ({condition})",
            text=response.get("text"),
            movement=response.get("movement"),
            game_number=game_number,
        )
        _handle_movement(response["movement"])
        return response["text"]
    
    log_conversation(player_id, "Human (Speech)", text=input_text, game_number=game_number)

    if condition == "LLM":
        response = llm.handle_speech(input_text, game_state)
    elif condition == "ALG":
        response = algorithmic.handle_speech_keyword(input_text)
    else:
        response = algorithmic.handle_speech(input_text)

    log_conversation(
        player_id,
        f"Pepper ({condition})",
        text=response.get("text"),
        movement=response.get("movement"),
        game_number=game_number,
    )

    _handle_movement(response["movement"])

    if not response.get("text"):
        _set_pepper_state("idle")

    return response["text"]


def handle_game_event(event, game_state):
    _set_pepper_state("processing")

    player_id = game_state.get("player_id")
    condition = game_state.get("condition", "LLM")
    game_number = game_state.get("current_game_number")

    log_conversation(player_id, "Game Event", text=str(event), game_number=game_number)

    if event.get("state") == "GAME_STARTED":
        response = _get_start_game_response(condition)
    elif condition == "LLM":
        response = llm.handle_game_event(event, game_state)
    elif condition == "ALG":
        response = algorithmic.handle_game_event_keyword(event, game_state)
    else:
        response = algorithmic.handle_game_event(event, game_state)

    log_conversation(
        player_id,
        f"Pepper ({condition})",
        text=response.get("text"),
        movement=response.get("movement"),
        game_number=game_number,
    )

    _handle_movement(response["movement"])

    speech_sent = False

    try:
        requests.post(
            SPEECH_API_URL,
            json={
                "text": response.get("text", ""),
                "state_version": game_state["state_version"],
            },
            timeout=5,
        )
        speech_sent = bool(response.get("text", ""))
    except Exception as exception:
        print(str(exception))

    if not speech_sent:
        _set_pepper_state("idle")
