import game
import interaction

from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException

app = Flask(__name__)


@app.route("/start-game", methods=["POST"])
def api_start_game():
    return game.start_game()


@app.route("/invest", methods=["POST"])
def api_invest():
    return game.invest(request)


@app.route("/handle-speech", methods=["POST"])
def api_handle_speech():
    try:
        data = request.get_json()
        input = data.get("text")

        response = interaction.handle_speech(input, game.get_state())
        return jsonify({"text": response})
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@app.errorhandler(HTTPException)
def handle_http_exception(exception):
    response = exception.get_response()

    response.data = jsonify(
        {
            "error": exception.name,
            "code": exception.code,
            "description": exception.description,
        }
    ).data
    response.content_type = "application/json"

    return response


@app.errorhandler(Exception)
def handle_exception(exception):
    return (
        jsonify(
            {
                "error": "Internal Server Error",
                "code": 500,
                "description": str(exception),
            }
        ),
        500,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
