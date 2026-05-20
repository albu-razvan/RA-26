import threading
import random
import copy
import ulid

from logger import log_game_observation
from interaction import handle_game_event, stop_output

from flask import jsonify

_game = None
_player_id = str(ulid.new())
_state_version = 0
# _condition = random.choice(["LLM", "Algorithmic"])
_condition = "LLM"

ROUND_BUDGET = 10
MAX_ROUNDS = 3

TRUSTWORTHY_MIN_MULTIPLIER = 1.2
TRUSTWORTHY_MAX_MULTIPLIER = 2.4

UNTRUSTWORTHY_MIN_MULTIPLIER = 0.2
UNTRUSTWORTHY_MAX_MULTIPLIER = 0.8

STD_DEV = 0.4


def _generate_return(investment, robot_type):
    global _player_id

    if investment == 0:
        return 0

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
    global _game, _player_id, _condition, _state_version

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
        }

    return {
        "game": copy.deepcopy(_game),
        "player_id": _player_id,
        "condition": _condition,
        "state": state,
        "state_version": _state_version,
    }


def start_game():
    global _game, _player_id, _condition, _state_version

    if _game is not None:
        _player_id = str(ulid.new())
        _condition = random.choice(["LLM", "Algorithmic"])

    _game = {
        "robot_type": random.choice(["trustworthy", "untrustworthy"]),
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
        }
    )


def reset_game():
    global _game, _player_id, _state_version

    stop_output()

    _game = None
    _player_id = str(ulid.new())
    _state_version += 1

    return jsonify({"status": "ok"})


def _reaction(event, state):
    handle_game_event(event, state)


def invest(request):
    global _game, _condition, _state_version

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
