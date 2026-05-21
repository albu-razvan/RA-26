import threading
import random
import copy
import os
import ulid

from logger import log_game_observation
from interaction import handle_game_event, stop_output

from flask import jsonify

_game = None
_player_id = str(ulid.new())
_state_version = 0
_games_played = 0

_CONTROL_SEQUENCE = ["LLM", "Algorithmic"]
_TRUST_SEQUENCE = ["trustworthy", "untrustworthy"]


def _parse_initial_control(value):
    normalized = str(value or "LLM").strip().upper()
    if normalized in ["ALG", "ALGORITHM", "ALGORITHMIC"]:
        return "Algorithmic"

    return "LLM"


def _parse_initial_trust(value):
    normalized = str(value or "T").strip().upper()
    if normalized in ["U", "UNTRUSTWORTHY", "UNTRUSTED"]:
        return "untrustworthy"

    return "trustworthy"


def _parse_positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except Exception:
        return default


_initial_condition = _parse_initial_control(os.environ.get("ROBOT_CONTROL_TYPE", "LLM"))
_initial_robot_type = _parse_initial_trust(os.environ.get("TRUSTWORTHINESS", "T"))
_participant_id = os.environ.get("PARTICIPANT_ID")
_game_limit = _parse_positive_int(
    os.environ.get("PARTICIPANT_GAME_LIMIT", os.environ.get("GAME_LIMIT", "2")),
    2,
)

_condition = _initial_condition

ROUND_BUDGET = 10
MAX_ROUNDS = _parse_positive_int(
    os.environ.get("GAME_ROUNDS", os.environ.get("MAX_ROUNDS_PER_GAME", "3")),
    3,
)

TRUSTWORTHY_MIN_MULTIPLIER = 1.2
TRUSTWORTHY_MAX_MULTIPLIER = 2.4

UNTRUSTWORTHY_MIN_MULTIPLIER = 0.2
UNTRUSTWORTHY_MAX_MULTIPLIER = 0.8

STD_DEV = 0.4


def _generate_return(investment, robot_type):
    global _player_id

    if investment == 0:
        return 0, 0, 0

    if robot_type == "trustworthy":
        min_multiplier = TRUSTWORTHY_MIN_MULTIPLIER
        max_multiplier = TRUSTWORTHY_MAX_MULTIPLIER
    else:
        min_multiplier = UNTRUSTWORTHY_MIN_MULTIPLIER
        max_multiplier = UNTRUSTWORTHY_MAX_MULTIPLIER

    min_return = int(round(min_multiplier * investment))
    max_return = int(round(max_multiplier * investment))

    returned = random.randint(min_return, max_return)

    if returned is None:
        returned = max_return

    return (
        returned,
        int(round(min_multiplier * ROUND_BUDGET)),
        int(round(max_multiplier * ROUND_BUDGET)),
    )


def get_state():
    global _game, _player_id, _condition, _state_version, _games_played

    games_remaining = max(0, _game_limit - _games_played)
    has_next_game = games_remaining > 0

    next_condition, next_robot_type = _get_game_parameters(_games_played)

    if _game is None:
        state = "GAME_NOT_STARTED"
    elif _game["round"] >= _game["max_rounds"]:
        state = "GAME_FINISHED"
    else:
        state = "GAME_ONGOING"

    if _game is None:
        return {
            "game": None,
            "player_id": _player_id,
            "condition": _condition,
            "state": state,
            "state_version": _state_version,
            "games_played": _games_played,
            "game_limit": _game_limit,
            "games_remaining": games_remaining,
            "has_next_game": has_next_game,
            "participant_complete": not has_next_game,
            "next_condition": next_condition,
            "next_trustworthiness": next_robot_type,
        }

    return {
        "game": copy.deepcopy(_game),
        "player_id": _player_id,
        "condition": _condition,
        "state": state,
        "state_version": _state_version,
        "games_played": _games_played,
        "game_limit": _game_limit,
        "games_remaining": games_remaining,
        "has_next_game": has_next_game,
        "participant_complete": not has_next_game,
        "current_trustworthiness": _game.get("robot_type"),
        "next_condition": next_condition,
        "next_trustworthiness": next_robot_type,
    }


def _get_game_parameters(game_index):
    control_start_idx = 0 if _initial_condition == "LLM" else 1
    trust_start_idx = 0 if _initial_robot_type == "trustworthy" else 1

    control_idx = (control_start_idx + (game_index % 2)) % 2
    trust_idx = (trust_start_idx + ((game_index // 2) % 2)) % 2

    return _CONTROL_SEQUENCE[control_idx], _TRUST_SEQUENCE[trust_idx]


def start_game():
    global _game, _player_id, _condition, _state_version

    if _game is not None and _game.get("round", 0) < _game.get("max_rounds", MAX_ROUNDS):
        return jsonify({"error": "A game is already in progress"}), 400

    if _games_played >= _game_limit:
        return jsonify({"error": "Participant has completed all assigned games"}), 400

    _condition, robot_type = _get_game_parameters(_games_played)

    if _games_played == 0 and _participant_id:
        _player_id = _participant_id

    _game = {
        "robot_type": robot_type,
        "bank": 0,
        "round": 0,
        "max_rounds": MAX_ROUNDS,
    }

    _state_version += 1
    current_state = get_state()

    handle_game_event(
        {"state": "GAME_STARTED"},
        current_state,
    )

    return jsonify(
        {
            "player_id": _player_id,
            "bank": 0,
            "round_budget": ROUND_BUDGET,
            "max_rounds": MAX_ROUNDS,
            "condition": _condition,
            "trustworthiness": robot_type,
            "games_played": _games_played,
            "games_remaining": max(0, _game_limit - _games_played),
            "game_limit": _game_limit,
        }
    )


def reset_game():
    global _game, _state_version

    stop_output()

    _game = None
    _state_version += 1

    return jsonify({"status": "ok"})


def _reaction(event, state):
    handle_game_event(event, state)


def invest(request):
    global _game, _condition, _state_version, _games_played

    if _game is None:
        return jsonify({"error": "No active game"}), 404

    data = request.get_json()

    player_id = data.get("player_id")
    investment = data.get("investment")

    if _player_id != player_id:
        return jsonify({"error": "Game ID does not match"}), 403

    if _game["round"] >= _game["max_rounds"]:
        return jsonify({"error": "Game already finished"}), 400

    if investment is None or investment < 0:
        return jsonify({"error": "Invalid investment"}), 400

    if investment > ROUND_BUDGET:
        return jsonify({"error": "Investment exceeds round budget"}), 400

    returned, min_returned, max_returned = _generate_return(
        investment, _game["robot_type"]
    )

    _game["bank"] += returned
    _game["round"] += 1

    response = {
        "round": _game["round"],
        "round_budget": ROUND_BUDGET,
        "invested": investment,
        "returned": returned,
        "min_returned": min_returned,
        "max_returned": max_returned,
        "bank": _game["bank"],
        "rounds_remaining": _game["max_rounds"] - _game["round"],
    }

    log_game_observation(
        player_id=player_id,
        round_number=_game["round"],
        trustworthiness=_game["robot_type"],
        condition=_condition,
        investment=investment,
        returned=returned,
        bank=_game["bank"],
    )

    if _game["round"] >= _game["max_rounds"]:
        _games_played += 1
        event_data = {
            "state": "GAME_FINISHED",
            "investment_from_human": investment,
            "returned_by_robot": returned,
        }
        _game = {
            "bank": _game["bank"],
            "round": _game["round"],
            "max_rounds": _game["max_rounds"],
        }
    else:
        event_data = {
            "state": "GAME_ONGOING",
            "investment_from_human": investment,
            "returned_by_robot": returned,
        }

    _state_version += 1
    current_state = get_state()
    threading.Thread(target=_reaction, args=(event_data, current_state), daemon=True).start()

    return jsonify(response)
