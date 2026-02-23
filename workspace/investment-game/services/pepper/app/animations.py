import time
import threading
from naoqi import ALProxy


# Refined by Gemini, based on Dharun Kumar's work
class PepperAnimation:
    POINT = "point"
    OPEN_ARM = "open_arm"
    WIDE_ARMS = "wide_arms"
    OFFER_HANDS = "offer_hands"
    LEAN = "lean"
    APPLAUSE = "applause"
    GOODBYE = "goodbye"
    STAND = "stand"

    def __init__(self, ip, port):
        self.motion = ALProxy("ALMotion", ip, port)
        self.posture = ALProxy("ALRobotPosture", ip, port)

        self._lock = threading.Lock()

        self.actions = {
            self.POINT: self._wrap(self.fast_point_at_user),
            self.OPEN_ARM: self._wrap(self.open_arm_in_front),
            self.WIDE_ARMS: self._wrap(self.wide_open_both_hands),
            self.OFFER_HANDS: self._wrap(self.slowly_offer_both_hands),
            self.LEAN: self._wrap(self.question_lean_front),
            self.APPLAUSE: self._wrap(self.applause),
            self.GOODBYE: self._wrap(self.goodbye),
            self.STAND: self._wrap(self.stand_upright),
        }

    def _wrap(self, func):
        def wrapper():
            if not self._lock.acquire(False):
                print("Robot is busy. Skipping animation.")
                return

            try:
                print("Starting animation...")
                func()

                time.sleep(1.0)
            except Exception as e:
                print("Error during animation: {}".format(e))
            finally:
                self.posture.goToPosture("Stand", 0.3)
                self._lock.release()

        return wrapper

    def trigger(self, action_name):
        if action_name in self.actions:
            print("Triggering animation: {}".format(action_name))

            self.actions[action_name]()
        else:
            print("Action '{}' not found.".format(action_name))

    def fast_point_at_user(self):
        names = [
            "RShoulderPitch",
            "RShoulderRoll",
            "RElbowYaw",
            "RElbowRoll",
            "RWristYaw",
            "RHand",
        ]
        angles = [0.0, -0.3, 1.2, -0.5, 0.0, 0.6]
        self.motion.angleInterpolationWithSpeed(names, angles, 0.2)
        self.motion.setAngles("RHand", 0.2, 0.1)
        time.sleep(2.0)

    def open_arm_in_front(self):
        names = ["LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LHand"]
        self.motion.setAngles("LHand", 0.1, 0.2)
        angles = [0.4, 0.4, -1.2, -0.7, 1.0]
        self.motion.angleInterpolationWithSpeed(names, angles, 0.15)
        time.sleep(2.0)

    def wide_open_both_hands(self):
        names = [
            "LShoulderPitch",
            "LShoulderRoll",
            "LElbowYaw",
            "LElbowRoll",
            "LHand",
            "RShoulderPitch",
            "RShoulderRoll",
            "RElbowYaw",
            "RElbowRoll",
            "RHand",
        ]
        # Start with hands closed
        self.motion.setAngles(["LHand", "RHand"], [0.1, 0.1], 0.2)
        # Flourish open
        angles = [0.4, 0.3, -1.2, -0.8, 1.0, 0.4, -0.3, 1.2, 0.8, 1.0]
        self.motion.angleInterpolationWithSpeed(names, angles, 0.15)
        time.sleep(2.5)

    def slowly_offer_both_hands(self):
        names = [
            "LShoulderPitch",
            "LShoulderRoll",
            "LElbowYaw",
            "LElbowRoll",
            "RShoulderPitch",
            "RShoulderRoll",
            "RElbowYaw",
            "RElbowRoll",
        ]
        angles = [0.5, 0.1, -1.0, -0.6, 0.5, -0.1, 1.0, 0.6]

        # Move arms and slowly open hands at the same time
        self.motion.post.angleInterpolationWithSpeed(names, angles, 0.08)
        self.motion.angleInterpolationWithSpeed(["LHand", "RHand"], [1.0, 1.0], 0.05)
        time.sleep(3.0)

    def question_lean_front(self):
        names = ["HipPitch", "KneePitch", "HeadPitch", "LHand", "RHand"]
        # Hands move to a 'half-open' relaxed state (0.5)
        angles = [-0.15, 0.08, 0.2, 0.5, 0.5]
        self.motion.angleInterpolationWithSpeed(names, angles, 0.1)
        time.sleep(2.5)

    def stand_upright(self):
        # Explicit action just triggers the reset via the wrapper
        pass

    def applause(self):
        names = [
            "LShoulderPitch",
            "LShoulderRoll",
            "LElbowYaw",
            "LElbowRoll",
            "LWristYaw",
            "LHand",
            "RShoulderPitch",
            "RShoulderRoll",
            "RElbowYaw",
            "RElbowRoll",
            "RWristYaw",
            "RHand",
        ]
        prep_angles = [0.6, 0.2, -1.5, -0.3, 0.0, 1.0, 0.6, -0.2, 1.5, 0.3, 0.0, 1.0]
        self.motion.angleInterpolationWithSpeed(names, prep_angles, 0.2)

        for _ in range(6):
            # Clap in
            self.motion.setAngles(["LElbowRoll", "RElbowRoll"], [-0.05, 0.05], 0.6)
            time.sleep(0.15)
            # Pull apart
            self.motion.setAngles(["LElbowRoll", "RElbowRoll"], [-0.35, 0.35], 0.6)
            time.sleep(0.15)

    def goodbye(self):
        names = ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RHand"]
        wave_prep = [0.3, -0.1, 1.0, 1.3, 1.0]
        self.motion.angleInterpolationWithSpeed(names, wave_prep, 0.2)

        for _ in range(4):
            # Wave Out
            self.motion.post.angleInterpolationWithSpeed("RHand", 1.0, 0.2)
            self.motion.angleInterpolationWithSpeed("RElbowYaw", 0.5, 0.2)
            # Wave In
            self.motion.post.angleInterpolationWithSpeed("RHand", 0.4, 0.2)
            self.motion.angleInterpolationWithSpeed("RElbowYaw", 1.2, 0.2)
