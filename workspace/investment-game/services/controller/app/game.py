import copy
import csv
import os
import random
import threading

from flask import jsonify

from interaction import handle_game_event, stop_output
from logger import has_conversation_log, log_game_observation

_game = None
_participant_id = None
_player_id = None
_state_version = 0
_games_played = 0
_condition = "LLM"
_active_schedule = []

GAMES_CSV_PATH = os.environ.get("GAMES_CSV_PATH", "/games.csv")

ROUND_BUDGET = 10

MAX_ROUNDS = 3
try:
    MAX_ROUNDS = max(
        1,
        int(os.environ.get("GAME_ROUNDS", os.environ.get("MAX_ROUNDS_PER_GAME", "3"))),
    )
except Exception:
    MAX_ROUNDS = 3

TRUSTWORTHY_MIN_MULTIPLIER = 1.2
TRUSTWORTHY_MAX_MULTIPLIER = 2.4

UNTRUSTWORTHY_MIN_MULTIPLIER = 0.2
UNTRUSTWORTHY_MAX_MULTIPLIER = 0.8


def _parse_condition(value):
    normalized = str(value or "").strip().upper()
    if normalized in {"ALG", "ALGORITHM", "ALGORITHMIC"}:
        return "ALG"
    if normalized in {"SEL-ALG", "SEL_ALG", "SELECTION_ALG", "SELECTION-ALG"}:
        return "SEL-ALG"
    if normalized in {
        "SEL",
        "SEL-LLM",
        "SEL_LLM",
        "SELECTOR",
        "SELECTION",
        "SELECTION_LLM",
        "SELECTION-LLM",
    }:
        return "SEL-LLM"
    return "LLM"


def _parse_trustworthiness(value):
    normalized = str(value or "").strip().upper()
    if normalized in {"T", "TRUSTWORTHY", "TRUSTED"}:
        return "trustworthy"
    if normalized in {"U", "UNTRUSTWORTHY", "UNTRUSTED"}:
        return "untrustworthy"
    raise ValueError("Unknown trustworthiness '{}'".format(value))


def _load_games_catalog(path):
    if not os.path.isfile(path):
        raise ValueError("games.csv was not found at {}".format(path))

    with open(path, mode="r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"player_id", "game", "trustworthiness", "condition"}
        missing_columns = required_columns.difference(set(reader.fieldnames or []))
        if missing_columns:
            raise ValueError(
                "games.csv is missing columns: {}".format(
                    ", ".join(sorted(missing_columns))
                )
            )

        by_player = {}
        for row in reader:
            player_id = str(row.get("player_id", "")).strip()
            if not player_id:
                continue

            try:
                game_number = int(str(row.get("game", "")).strip())
                if game_number <= 0:
                    raise ValueError
            except Exception:
                raise ValueError(
                    "Invalid game number '{}' for player '{}'".format(
                        row.get("game"), player_id
                    )
                )

            entry = {
                "game": game_number,
                "trustworthiness": _parse_trustworthiness(row.get("trustworthiness")),
                "condition": _parse_condition(row.get("condition")),
            }
            by_player.setdefault(player_id, []).append(entry)

    for player_id, entries in by_player.items():
        entries.sort(key=lambda item: item["game"])
        seen = set()
        for entry in entries:
            game_number = entry["game"]
            if game_number in seen:
                raise ValueError(
                    "Duplicate game '{}' for player '{}' in games.csv".format(
                        game_number, player_id
                    )
                )
            seen.add(game_number)

    return by_player


def _current_game_limit():
    return len(_active_schedule)


def _next_assignment():
    if _games_played >= _current_game_limit():
        return None
    return _active_schedule[_games_played]


def _generate_return(investment, robot_type):
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


def configure_participant(participant_id, override=False):
    global _game, _participant_id, _player_id, _games_played, _state_version, _condition, _active_schedule

    normalized_participant_id = str(participant_id or "").strip()
    if not normalized_participant_id:
        return jsonify({"error": "participant_id is required"}), 400

    if _game is not None and _game.get("round", 0) < _game.get("max_rounds", MAX_ROUNDS):
        return jsonify({"error": "Cannot change participant while a game is in progress"}), 400

    try:
        catalog = _load_games_catalog(GAMES_CSV_PATH)
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500

    participant_schedule = catalog.get(normalized_participant_id)
    if not participant_schedule:
        return (
            jsonify(
                {
                    "error": "Participant '{}' does not exist in games.csv".format(
                        normalized_participant_id
                    )
                }
            ),
            404,
        )

    already_run = has_conversation_log(normalized_participant_id)
    if already_run and not override:
        return (
            jsonify(
                {
                    "error": "Participant '{}' already has conversation logs".format(
                        normalized_participant_id
                    ),
                    "override_required": True,
                }
            ),
            409,
        )

    stop_output()

    _participant_id = normalized_participant_id
    _player_id = normalized_participant_id
    _active_schedule = copy.deepcopy(participant_schedule)
    _games_played = 0
    _game = None
    _condition = _active_schedule[0]["condition"] if _active_schedule else "LLM"
    _state_version += 1

    next_game = _next_assignment()

    return jsonify(
        {
            "status": "ok",
            "participant_id": _participant_id,
            "games_played": _games_played,
            "game_limit": _current_game_limit(),
            "games_remaining": _current_game_limit(),
            "next_condition": next_game.get("condition") if next_game else None,
            "next_trustworthiness": next_game.get("trustworthiness") if next_game else None,
            "next_game_number": next_game.get("game") if next_game else None,
            "override_applied": bool(already_run and override),
        }
    )


def get_state():
    global _game, _state_version, _games_played

    game_limit = _current_game_limit()
    games_remaining = max(0, game_limit - _games_played)
    has_next_game = games_remaining > 0

    next_game = _next_assignment()
    next_condition = next_game.get("condition") if next_game else None
    next_trustworthiness = next_game.get("trustworthiness") if next_game else None
    next_game_number = next_game.get("game") if next_game else None

    if _game is None:
        state = "GAME_NOT_STARTED"
    elif _game["round"] >= _game["max_rounds"]:
        state = "GAME_FINISHED"
    else:
        state = "GAME_ONGOING"

    current_game_number = None
    if _game is not None:
        current_game_number = _game.get("game_number")
    else:
        current_game_number = next_game_number

    base_state = {
        "player_id": _player_id,
        "participant_id": _participant_id,
        "condition": _condition,
        "state": state,
        "state_version": _state_version,
        "games_played": _games_played,
        "game_limit": game_limit,
        "games_remaining": games_remaining,
        "has_next_game": has_next_game,
        "participant_complete": game_limit > 0 and not has_next_game,
        "participant_configured": bool(_participant_id),
        "current_game_number": current_game_number,
        "next_condition": next_condition,
        "next_trustworthiness": next_trustworthiness,
        "next_game_number": next_game_number,
    }

    if _game is None:
        base_state["game"] = None
        return base_state

    base_state["game"] = copy.deepcopy(_game)
    base_state["current_trustworthiness"] = _game.get("robot_type")
    return base_state


def start_game():
    global _game, _condition, _state_version

    if not _participant_id:
        return jsonify({"error": "No participant configured"}), 400

    if _game is not None and _game.get("round", 0) < _game.get("max_rounds", MAX_ROUNDS):
        return jsonify({"error": "A game is already in progress"}), 400

    assignment = _next_assignment()
    if assignment is None:
        return jsonify({"error": "Participant has completed all assigned games"}), 400

    _condition = assignment["condition"]
    robot_type = assignment["trustworthiness"]
    game_number = assignment["game"]

    _game = {
        "game_number": game_number,
        "condition": _condition,
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
            "participant_id": _participant_id,
            "game_number": game_number,
            "bank": 0,
            "round_budget": ROUND_BUDGET,
            "max_rounds": MAX_ROUNDS,
            "condition": _condition,
            "trustworthiness": robot_type,
            "games_played": _games_played,
            "games_remaining": max(0, _current_game_limit() - _games_played),
            "game_limit": _current_game_limit(),
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

    data = request.get_json() or {}

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

    returned, min_returned, max_returned = _generate_return(investment, _game["robot_type"])

    _game["bank"] += (ROUND_BUDGET - investment + returned)
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
        game_number=_game.get("game_number"),
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
            "game_number": _game["game_number"],
            "condition": _condition,
            "robot_type": _game["robot_type"],
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
