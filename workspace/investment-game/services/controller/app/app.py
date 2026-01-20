from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException
from logger import log_game_observation
import random
import ulid

app = Flask(__name__)

games = {}

ROUND_BUDGET = 10
MAX_ROUNDS = 20

# Expected multipliers (long-run behavior)
TRUSTWORTHY_MEAN = 1.4
UNTRUSTWORTHY_MEAN = 0.7

STD_DEV = 0.4
MIN_MULTIPLIER = 0.0
MAX_MULTIPLIER = 3.0


def generate_return(investment, robot_type):
    if investment == 0:
        return 0

    if robot_type == "trustworthy":
        mean = TRUSTWORTHY_MEAN
    else:
        mean = UNTRUSTWORTHY_MEAN

    multiplier = random.gauss(mean, STD_DEV)
    multiplier = max(MIN_MULTIPLIER, min(multiplier, MAX_MULTIPLIER))

    return int(round(investment * multiplier))


@app.route("/start-game", methods=["POST"])
def start_game():
    player_id = str(ulid.new())

    games[player_id] = {
        "robot_type": random.choice(["trustworthy", "untrustworthy"]),
        "bank": 0,
        "round": 0,
        "max_rounds": MAX_ROUNDS,
    }

    return jsonify({
        "player_id": player_id,
        "bank": 0,
        "round_budget": ROUND_BUDGET,
        "max_rounds": MAX_ROUNDS
    })


@app.route("/invest", methods=["POST"])
def invest():
    data = request.get_json()

    player_id = data.get("player_id")
    investment = data.get("investment")

    if not player_id or player_id not in games:
        return jsonify({"error": "Invalid player_id"}), 404

    game = games[player_id]

    if game["round"] >= game["max_rounds"]:
        return jsonify({"error": "Game already finished"}), 400

    if investment is None or investment < 0:
        return jsonify({"error": "Invalid investment"}), 400

    if investment > ROUND_BUDGET:
        return jsonify({"error": "Investment exceeds round budget"}), 400

    returned = generate_return(investment, game["robot_type"])

    game["bank"] += returned
    game["round"] += 1

    response = {
        "round": game["round"],
        "round_budget": ROUND_BUDGET,
        "invested": investment,
        "returned": returned,
        "min_returned": int(investment * MIN_MULTIPLIER),
        "max_returned": int(investment * MAX_MULTIPLIER),
        "bank": game["bank"],
        "rounds_remaining": game["max_rounds"] - game["round"]
    }

    log_game_observation(
        player_id=player_id,
        round_number=game["round"],
        robot_type=game["robot_type"],
        investment=investment,
        returned=returned,
        bank=game["bank"]
    )

    if game["round"] >= game["max_rounds"]:    
        del games[player_id]

    return jsonify(response)

@app.errorhandler(HTTPException)
def handle_http_exception(exception):
    response = exception.get_response()

    response.data = jsonify({
        "error": exception.name,
        "code": exception.code,
        "description": exception.description
    }).data
    response.content_type = "application/json"

    return response

@app.errorhandler(Exception)
def handle_exception(exception):
    return jsonify({
        "error": "Internal Server Error",
        "description": str(exception)
    }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
