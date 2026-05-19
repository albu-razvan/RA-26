import threading
import os
import time
import requests

from bottle import route, run, request, response
from animations import PepperAnimation
from naoqi import ALProxy

ALLOWED_STATES = ["idle", "listening", "processing", "speaking"]
ROBOT_IP = os.environ.get("ROBOT_IP", "192.168.0.100")
PORT = 9559
ROBOT_HANDLER_HOST = "127.0.0.1"
ROBOT_HANDLER_CTRL_PORT = 9703
SPEECH_API_URL = "http://speech:9701"
TACTILE_KEYS = ["FrontTactilTouched", "MiddleTactilTouched", "RearTactilTouched"]
TACTILE_POLL_SECONDS = 0.05
TACTILE_COOLDOWN_SECONDS = 0.75


def _notify_speech_interrupt():
    try:
        requests.post("{}/interrupt".format(SPEECH_API_URL), timeout=0.3)
    except Exception as exception:
        print("Failed to notify speech service: {}".format(exception))


def _is_head_touched():
    try:
        for key in TACTILE_KEYS:
            if float(memory.getData(key) or 0.0) > 0.5:
                return True
    except Exception:
        return False

    return False


def _head_touch_interrupt_loop():
    global audio_player

    last_touch_state = False
    last_interrupt_time = 0.0

    while True:
        touched = _is_head_touched()

        if touched and not last_touch_state:
            now = time.time()
            if now - last_interrupt_time >= TACTILE_COOLDOWN_SECONDS:
                try:
                    audio_player.stopAll()
                    _notify_speech_interrupt()
                    print("Head touch detected: interrupt triggered")
                except Exception as exception:
                    print("Head touch interrupt failed: {}".format(exception))
                last_interrupt_time = now

        last_touch_state = touched
        threading.Event().wait(TACTILE_POLL_SECONDS)


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


@route("/interrupt", method="POST")
def handle_interrupt():
    try:
        audio_player = ALProxy("ALAudioPlayer", ROBOT_IP, PORT)
        audio_player.stopAll()
        _notify_speech_interrupt()
        return {"status": "interrupted"}
    except Exception as exception:
        response.status = 500
        return {"error": str(exception)}


def setup_robot():
    global anim, memory, audio_player

    life = ALProxy("ALAutonomousLife", ROBOT_IP, PORT)
    awareness = ALProxy("ALBasicAwareness", ROBOT_IP, PORT)
    motion = ALProxy("ALMotion", ROBOT_IP, PORT)
    posture = ALProxy("ALRobotPosture", ROBOT_IP, PORT)
    memory = ALProxy("ALMemory", ROBOT_IP, PORT)
    audio_player = ALProxy("ALAudioPlayer", ROBOT_IP, PORT)

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

    thread = threading.Thread(target=_head_touch_interrupt_loop)
    thread.daemon = True
    thread.start()


if __name__ == "__main__":
    setup_robot()

    run(host="0.0.0.0", port=8080)
