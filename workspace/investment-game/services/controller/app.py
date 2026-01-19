from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException
import uuid
import random

app = Flask(__name__)

games = {}

STARTING_BANK = 0
MAX_ROUNDS = 10

TRUSTWORTHY_RETURN_RATE = 0.8
UNTRUSTWORTHY_RETURN_RATE = 0.3

TRUST_MULTIPLIER = 2.0

def generate_return(investment, robot_type):
    if robot_type == "trustworthy":
        success = random.random() < TRUSTWORTHY_RETURN_RATE
    else:
        success = random.random() < UNTRUSTWORTHY_RETURN_RATE

    if success:
        return int(investment * TRUST_MULTIPLIER)
    else:
        return 0

@app.route("/start-game", methods=["POST"])
def start_game():
    player_id = str(uuid.uuid4())

    games[player_id] = {
        "robot_type": random.choice(["trustworthy", "untrustworthy"]),
        "bank": STARTING_BANK,
        "round": 0,
        "max_rounds": MAX_ROUNDS,
    }

    return jsonify({
        "player_id": player_id,
        "bank": STARTING_BANK,
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

    if investment is None or investment <= 0:
        return jsonify({"error": "Invalid investment"}), 400

    if investment > game["bank"]:
        return jsonify({"error": "Insufficient funds"}), 400

    returned = generate_return(investment, game["robot_type"])

    game["bank"] += returned - investment
    game["round"] += 1

    response = {
        "round": game["round"],
        "invested": investment,
        "returned": returned,
        "bank": game["bank"],
        "rounds_remaining": game["max_rounds"] - game["round"]
    }

    if game["round"] >= game["max_rounds"]:
        # TODO: save outcome to csv
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
