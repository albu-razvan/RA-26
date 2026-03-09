import threading
import os

from bottle import route, run, request, response
from animations import PepperAnimation
from naoqi import ALProxy

ALLOWED_STATES = ["idle", "listening", "processing", "speaking"]
ROBOT_IP = os.environ.get("ROBOT_IP", "192.168.0.100")
PORT = 9559


@route("/animate", method="POST")
def handle_animation():
    global anim

    data = request.json

    if not data or "action" not in data:
        response.status = 400
        return {"error": "JSON body must contain 'action'"}

    action_key = data["action"]
    if action_key in anim.actions:
        threading.Thread(target=anim.actions[action_key]).start()
        return {"status": "triggered", "action": action_key}
    else:
        response.status = 404
        return {"error": "Action '{}' not found".format(action_key)}


@route("/set-state", method="POST")
def handle_state():
    global memory

    data = request.json

    if not data or "state" not in data:
        response.status = 400
        return {"error": "JSON body must contain 'state'"}

    try:
        state = str(data["state"])
        if state not in ALLOWED_STATES:
            state = "idle"

        memory.raiseEvent("GlobalEyeState", state)

        return {"status": "success", "state": data["state"]}
    except Exception as exception:
        response.status = 500
        return {"error": str(exception)}


def setup_robot():
    global anim, memory

    life = ALProxy("ALAutonomousLife", ROBOT_IP, PORT)
    awareness = ALProxy("ALBasicAwareness", ROBOT_IP, PORT)
    motion = ALProxy("ALMotion", ROBOT_IP, PORT)
    posture = ALProxy("ALRobotPosture", ROBOT_IP, PORT)
    memory = ALProxy("ALMemory", ROBOT_IP, PORT)

    if life.getState() != "disabled":
        life.setState("disabled")

    motion.wakeUp()
    posture.goToPosture("Stand", 0.5)

    awareness.setEngagementMode("FullyEngaged")
    awareness.setTrackingMode("Head")
    awareness.setStimulusDetectionEnabled("People", True)
    awareness.setStimulusDetectionEnabled("Sound", True)
    awareness.setEnabled(True)

    anim = PepperAnimation(ROBOT_IP, PORT)


if __name__ == "__main__":
    setup_robot()

    run(host="0.0.0.0", port=8080)
