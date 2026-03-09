import os
import csv
from datetime import datetime

OBSERVATIONS_DIR = "../observations"
CSV_FILE_PATH = os.path.join(OBSERVATIONS_DIR, "game_observations.csv")
CONVERSATIONS_DIR = os.path.join(OBSERVATIONS_DIR, "conversations")

FIELDNAMES = [
    "player_id",
    "round",
    "trustworthiness",
    "condition",
    "investment",
    "returned",
    "bank",
]


def log_game_observation(
    player_id, round_number, trustworthiness, condition, investment, returned, bank
):
    os.makedirs(OBSERVATIONS_DIR, exist_ok=True)

    file_exists = os.path.isfile(CSV_FILE_PATH)

    with open(CSV_FILE_PATH, mode="a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "player_id": player_id,
                "round": round_number,
                "trustworthiness": trustworthiness,
                "condition": condition,
                "investment": investment,
                "returned": returned,
                "bank": bank,
            }
        )


def log_conversation(player_id, sender, text=None, movement=None):
    if not player_id:
        return

    os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
    file_path = os.path.join(CONVERSATIONS_DIR, f"{player_id}.txt")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(file_path, mode="a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {sender}:\n")

        if text is not None:
            file.write(f"  Said: {text}\n")

        if movement is not None:
            file.write(f"  Performed movement: {movement}\n")

        file.write("\n")
