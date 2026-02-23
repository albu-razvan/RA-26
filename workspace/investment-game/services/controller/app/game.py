import random
import copy
import ulid

from logger import log_game_observation
from interaction import handle_game_event
from interaction.llm import generate_return
from flask import jsonify

_game = None
_player_id = str(ulid.new())
_condition = random.choice(["LLM", "Algorithmic"])

ROUND_BUDGET = 10
MAX_ROUNDS = 20

# Expected multipliers (long-run behavior)
TRUSTWORTHY_MEAN = 1.4
UNTRUSTWORTHY_MEAN = 0.7

STD_DEV = 0.4
MIN_MULTIPLIER = 0.0
MAX_MULTIPLIER = 3.0


def _generate_return(investment, robot_type, condition):
    global _player_id

    if investment == 0:
        return 0

    if robot_type == "trustworthy":
        mean = TRUSTWORTHY_MEAN
    else:
        mean = UNTRUSTWORTHY_MEAN

    if condition == "LLM":
        returned = generate_return(
            investment=investment,
            long_term_return_mean=mean,
            min=MIN_MULTIPLIER * ROUND_BUDGET,
            max=MAX_MULTIPLIER * ROUND_BUDGET,
            player_id=_player_id,
        )

        if returned is not None:
            return returned

    multiplier = random.gauss(mean, STD_DEV)
    multiplier = max(MIN_MULTIPLIER, min(multiplier, MAX_MULTIPLIER))

    return int(round(investment * multiplier))


def get_state():
    global _game, _player_id, _condition

    if _game == None:
        return {"game": None, "player_id": _player_id, "condition": _condition}

    return {
        "game": copy.deepcopy(_game),
        "player_id": _player_id,
        "condition": _condition,
    }


def start_game():
    global _game, _player_id, _condition

    if _game is not None:
        _player_id = str(ulid.new())
        _condition = random.choice(["LLM", "Algorithmic"])

    _game = {
        "robot_type": random.choice(["trustworthy", "untrustworthy"]),
        "bank": 0,
        "round": 0,
        "max_rounds": MAX_ROUNDS,
    }

    handle_game_event(
        {"state": "GAME_STARTED"},
        get_state(),
    )

    return jsonify(
        {
            "player_id": _player_id,
            "bank": 0,
            "round_budget": ROUND_BUDGET,
            "max_rounds": MAX_ROUNDS,
        }
    )


def invest(request):
    global _game, _condition

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

    returned = _generate_return(investment, _game["robot_type"], _condition)

    _game["bank"] += returned
    _game["round"] += 1

    response = {
        "round": _game["round"],
        "round_budget": ROUND_BUDGET,
        "invested": investment,
        "returned": returned,
        "min_returned": int(investment * MIN_MULTIPLIER),
        "max_returned": int(investment * MAX_MULTIPLIER),
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
        handle_game_event(
            {
                "state": "GAME_FINISHED",
                "investment_from_human": investment,
                "returned_by_robot": returned,
            },
            get_state(),
        )

        _game = {
            "bank": _game["bank"],
            "round": _game["round"],
            "max_rounds": _game["max_rounds"],
        }
    else:
        handle_game_event(
            {
                "state": "GAME_ONGOING",
                "investment_from_human": investment,
                "returned_by_robot": returned,
            },
            get_state(),
        )

    return jsonify(response)
