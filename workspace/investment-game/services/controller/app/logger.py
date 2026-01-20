import os
import csv

OBSERVATIONS_DIR = "../observations"
CSV_FILE_PATH = os.path.join(OBSERVATIONS_DIR, "game_observations.csv")
FIELDNAMES = ["player_id", "round", "trustworthiness", "investment", "returned", "bank"]

def log_game_observation(player_id, round_number, robot_type, investment, returned, bank):
    os.makedirs(OBSERVATIONS_DIR, exist_ok=True)

    file_exists = os.path.isfile(CSV_FILE_PATH)

    with open(CSV_FILE_PATH, mode="a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "player_id": player_id,
            "round": round_number,
            "trustworthiness": robot_type,
            "investment": investment,
            "returned": returned,
            "bank": bank
        })
