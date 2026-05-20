import requests

CONTROLLER_URL = "http://controller:8000"
PEPPER_HANDLER_URL = "http://pepper:8080"


def get_controller_status(timeout=0.2):
    try:
        response = requests.get("{}/status".format(CONTROLLER_URL), timeout=timeout)
        return response.json()
    except Exception as exception:
        print("Error fetching status: {}".format(exception))
        return {"state": "GAME_NOT_STARTED", "state_version": 0}


def is_game_not_started(status):
    return status.get("state", "GAME_NOT_STARTED") == "GAME_NOT_STARTED"


def interrupt_pepper(timeout=1):
    requests.post("{}/interrupt".format(PEPPER_HANDLER_URL), timeout=timeout)


def set_pepper_state(state, timeout=1):
    requests.post(
        "{}/set-state".format(PEPPER_HANDLER_URL),
        json={"state": state},
        timeout=timeout,
    )


def animate_pepper(action, timeout=1):
    requests.post(
        "{}/animate".format(PEPPER_HANDLER_URL),
        json={"action": action},
        timeout=timeout,
    )
