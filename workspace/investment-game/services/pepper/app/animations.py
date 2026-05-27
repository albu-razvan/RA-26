import time
import threading
from naoqi import ALProxy


# Refined by ChatGPT, based on Dharun Kumar's work
class PepperAnimation:
    POINT = "point"
    OPEN_ARM = "open_arm"
    WIDE_ARMS = "wide_arms"
    OFFER_HANDS = "offer_hands"
    LEAN = "lean"
    APPLAUSE = "applause"
    GOODBYE = "goodbye"
    LISTEN = "listen"
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
            self.LISTEN: self._wrap(self.listen, reset_posture=False),
            self.STAND: self._wrap(self.stand_upright, reset_posture=False),
        }

    def _wrap(self, func, reset_posture=True):
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
                if reset_posture:
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
        # Look toward the user first
        self.motion.post.angleInterpolationWithSpeed(
            ["HeadYaw", "HeadPitch"],
            [0.12, -0.04],
            0.10,
        )

        # Small anticipation movement
        self.motion.angleInterpolationWithSpeed(
            [
                "RShoulderPitch",
                "RShoulderRoll",
                "RElbowYaw",
                "RElbowRoll",
            ],
            [
                0.75,
                -0.05,
                0.8,
                0.9,
            ],
            0.18,
        )

        time.sleep(0.12)

        # Main pointing motion
        names = [
            "HeadYaw",
            "HeadPitch",

            "HipPitch",
            "HipRoll",

            "RShoulderPitch",
            "RShoulderRoll",
            "RElbowYaw",
            "RElbowRoll",
            "RWristYaw",
            "RHand",

            "LShoulderPitch",
            "LShoulderRoll",
        ]

        angles = [
            0.08,      # HeadYaw
            -0.06,     # HeadPitch

            -0.06,     # HipPitch slight lean
            -0.04,     # HipRoll

            0.02,      # RShoulderPitch
            -0.22,     # RShoulderRoll
            1.35,      # RElbowYaw
            0.18,      # RElbowRoll
            -0.28,     # RWristYaw
            1.0,       # RHand open

            1.4,       # Left arm relaxed
            0.18,
        ]

        self.motion.angleInterpolationWithSpeed(names, angles, 0.23)

        # Tiny wrist/finger micro-motions while holding pose
        for _ in range(3):
            self.motion.setAngles(
                ["RWristYaw", "RHand"],
                [-0.18, 0.85],
                0.08,
            )

            time.sleep(0.14)

            self.motion.setAngles(
                ["RWristYaw", "RHand"],
                [-0.32, 1.0],
                0.08,
            )

            time.sleep(0.14)

        # Soft settle
        self.motion.angleInterpolationWithSpeed(
            ["HeadYaw", "RWristYaw"],
            [0.02, -0.22],
            0.05,
        )

        time.sleep(0.8)

    def open_arm_in_front(self):
        # Engage with the user first
        self.motion.post.angleInterpolationWithSpeed(
            ["HeadYaw", "HeadPitch"],
            [-0.08, -0.03],
            0.08,
        )

        # Slight torso lean for warmth
        self.motion.angleInterpolationWithSpeed(
            ["HipPitch", "HipRoll"],
            [-0.05, 0.035],
            0.06,
        )

        # Anticipation: arm starts close to body
        prep_names = [
            "LShoulderPitch",
            "LShoulderRoll",
            "LElbowYaw",
            "LElbowRoll",
            "LWristYaw",
            "LHand",
        ]

        prep_angles = [
            0.9,
            0.15,
            -0.6,
            -1.0,
            -0.2,
            0.2,
        ]

        self.motion.angleInterpolationWithSpeed(
            prep_names,
            prep_angles,
            0.18,
        )

        time.sleep(0.15)

        # Main expressive offering motion
        names = [
            "HeadYaw",
            "HeadPitch",

            "LShoulderPitch",
            "LShoulderRoll",
            "LElbowYaw",
            "LElbowRoll",
            "LWristYaw",
            "LHand",

            "RShoulderPitch",
            "RShoulderRoll",
        ]

        angles = [
            -0.04,     # HeadYaw
            -0.05,     # HeadPitch

            0.32,      # LShoulderPitch
            0.42,      # LShoulderRoll
            -1.25,     # LElbowYaw
            -0.55,     # LElbowRoll
            -0.10,     # LWristYaw
            1.0,       # Open hand

            1.45,      # Right arm relaxed
            -0.08,
        ]

        self.motion.angleInterpolationWithSpeed(
            names,
            angles,
            0.14,
        )

        # Subtle hand articulation while holding
        for _ in range(2):
            self.motion.setAngles(
                ["LHand", "LWristYaw"],
                [0.82, 0.05],
                0.05,
            )

            time.sleep(0.18)

            self.motion.setAngles(
                ["LHand", "LWristYaw"],
                [1.0, -0.08],
                0.05,
            )

            time.sleep(0.18)

        # Gentle settle
        self.motion.angleInterpolationWithSpeed(
            ["HeadYaw", "HipPitch"],
            [0.0, -0.03],
            0.04,
        )

        time.sleep(1.0)

    def wide_open_both_hands(self):
        # Make eye contact first
        self.motion.post.angleInterpolationWithSpeed(
            ["HeadYaw", "HeadPitch"],
            [0.0, -0.05],
            0.08,
        )

        # Slight excited lean forward
        self.motion.angleInterpolationWithSpeed(
            ["HipPitch", "HipRoll"],
            [-0.08, 0.03],
            0.06,
        )

        # Anticipation pose (arms slightly inward)
        prep_names = [
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

        prep_angles = [
            0.95,
            0.12,
            -0.7,
            -1.0,
            -0.1,
            0.2,

            0.95,
            -0.12,
            0.7,
            1.0,
            0.1,
            0.2,
        ]

        self.motion.angleInterpolationWithSpeed(
            prep_names,
            prep_angles,
            0.18,
        )

        time.sleep(0.18)

        # Main wide opening gesture
        names = [
            "HeadYaw",
            "HeadPitch",

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

        angles = [
            0.03,      # HeadYaw
            -0.08,     # HeadPitch

            0.28,      # Left arm
            0.62,
            -1.35,
            -0.42,
            -0.15,
            1.0,

            0.28,      # Right arm
            -0.62,
            1.35,
            0.42,
            0.15,
            1.0,
        ]

        self.motion.angleInterpolationWithSpeed(
            names,
            angles,
            0.16,
        )

        # Add expressive flourish
        for _ in range(2):
            self.motion.setAngles(
                ["LWristYaw", "RWristYaw"],
                [-0.05, 0.05],
                0.08,
            )

            self.motion.setAngles(
                ["HeadYaw"],
                [0.06],
                0.04,
            )

            time.sleep(0.18)

            self.motion.setAngles(
                ["LWristYaw", "RWristYaw"],
                [-0.22, 0.22],
                0.08,
            )

            self.motion.setAngles(
                ["HeadYaw", "HipRoll"],
                [0.06, 0.05],
                0.04,
            )

            self.motion.setAngles(
                ["HeadYaw"],
                [-0.06],
                0.04,
            )

            time.sleep(0.18)

        # Soft settling motion
        self.motion.angleInterpolationWithSpeed(
            ["HeadYaw", "HipPitch", "HipRoll"],
            [0.0, -0.03, -0.05],
            0.04,
        )

        time.sleep(1.2)

    def slowly_offer_both_hands(self):
        # Gentle attention toward the user
        self.motion.post.angleInterpolationWithSpeed(
            ["HeadYaw", "HeadPitch"],
            [0.04, -0.08],
            0.05,
        )

        # Soft forward lean
        self.motion.angleInterpolationWithSpeed(
            ["HipPitch"],
            [-0.07],
            0.04,
        )

        # Start with hands partially closed near torso
        prep_names = [
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

        prep_angles = [
            0.95,
            0.10,
            -0.8,
            -1.1,
            -0.2,
            0.15,

            0.95,
            -0.10,
            0.8,
            1.1,
            0.2,
            0.15,
        ]

        self.motion.angleInterpolationWithSpeed(
            prep_names,
            prep_angles,
            0.10,
        )

        time.sleep(0.25)

        # Main offering motion
        arm_names = [
            "LShoulderPitch",
            "LShoulderRoll",
            "LElbowYaw",
            "LElbowRoll",
            "LWristYaw",

            "RShoulderPitch",
            "RShoulderRoll",
            "RElbowYaw",
            "RElbowRoll",
            "RWristYaw",
        ]

        arm_angles = [
            0.42,
            0.18,
            -1.05,
            -0.58,
            -0.04,

            0.42,
            -0.18,
            1.05,
            0.58,
            0.04,
        ]

        # Move arms slowly and naturally
        self.motion.post.angleInterpolationWithSpeed(
            arm_names,
            arm_angles,
            0.055,
        )

        # Open hands gradually while arms extend
        for openness in [0.25, 0.45, 0.65, 0.85, 1.0]:
            self.motion.setAngles(
                ["LHand", "RHand"],
                [openness, openness],
                0.03,
            )

            # Tiny wrist articulation
            self.motion.setAngles(
                ["LWristYaw", "RWristYaw"],
                [-0.02, 0.02],
                0.02,
            )

            time.sleep(0.22)

        # Subtle expressive hold
        for _ in range(2):
            self.motion.setAngles(
                ["HeadYaw"],
                [0.05],
                0.02,
            )

            time.sleep(0.3)

            self.motion.setAngles(
                ["HeadYaw"],
                [-0.05],
                0.02,
            )

            time.sleep(0.3)

        # Gentle settle into final pose
        self.motion.angleInterpolationWithSpeed(
            ["HeadYaw", "HeadPitch"],
            [0.0, -0.04],
            0.03,
        )

        time.sleep(1.0)

    def question_lean_front(self):
        # Curious head movement first
        self.motion.post.angleInterpolationWithSpeed(
            ["HeadYaw", "HeadPitch"],
            [0.18, 0.06],
            0.06,
        )

        # Slight anticipation pull-back
        self.motion.angleInterpolationWithSpeed(
            ["HipPitch"],
            [0.03],
            0.05,
        )

        time.sleep(0.12)

        # Main curious lean-in pose
        names = [
            "HeadYaw",
            "HeadPitch",

            "HipPitch",
            "HipRoll",
            "KneePitch",

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

        angles = [
            0.12,      # HeadYaw
            0.14,      # HeadPitch

            -0.09,     # Lean forward
            -0.05,     # HipRoll
            0.09,      # Slight knee bend

            0.72,      # Left arm
            0.22,
            -1.0,
            -0.85,
            -0.15,
            0.55,

            0.72,      # Right arm
            -0.22,
            1.0,
            0.85,
            0.15,
            0.55,
        ]

        self.motion.angleInterpolationWithSpeed(
            names,
            angles,
            0.08,
        )

        # Micro expressive movements while listening
        for _ in range(2):
            # Tiny head tilt
            self.motion.setAngles(
                ["HeadYaw", "HeadPitch"],
                [0.20, 0.11],
                0.03,
            )

            # Slight hand adjustment
            self.motion.setAngles(
                ["LHand", "RHand"],
                [0.65, 0.65],
                0.02,
            )

            time.sleep(0.35)

            self.motion.setAngles(
                ["HeadYaw", "HeadPitch"],
                [0.08, 0.16],
                0.03,
            )

            self.motion.setAngles(
                ["LHand", "RHand"],
                [0.5, 0.5],
                0.02,
            )

            time.sleep(0.35)

        # Small settling motion
        self.motion.angleInterpolationWithSpeed(
            ["HeadYaw", "HeadPitch"],
            [0.05, 0.10],
            0.03,
        )

        time.sleep(1.0)

    def listen(self):
        # Subtle lean toward the user
        self.motion.angleInterpolationWithSpeed(
            ["HipPitch", "HipRoll"],
            [-0.12, 0.03],
            0.05,
        )

    def stand_upright(self):
        # Explicit action just triggers the reset via the wrapper
        pass

    def applause(self):
        # Head engagement
        self.motion.angleInterpolationWithSpeed(
            ["HeadYaw", "HeadPitch"],
            [0.0, -0.08],
            0.3,
        )

        # Slight forward lean (helps reach space)
        self.motion.angleInterpolationWithSpeed(
            ["HipPitch"],
            [-0.06],
            0.3,
        )

        names = [
            "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll",
            "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll",
        ]

        # OPEN POSITION (hands clearly apart)
        open_pose = [
            0.7,  0.35, -1.2, -1.2,
            0.7, -0.35,  1.2,  1.2,
        ]

        # IMPORTANT: FORCE inward convergence more aggressively
        # Right arm must cross slightly inward, not stay "wide"
        clap_pose = [
            0.55,  0.05, -1.0, -0.25,
            0.55, -0.05,  1.0,  0.25,
        ]

        self.motion.angleInterpolationWithSpeed(names, open_pose, 0.3)
        time.sleep(0.2)

        for i in range(2):

            # Move IN (this is where contact happens)
            self.motion.angleInterpolationWithSpeed(names, clap_pose, 0.08)

            # tiny head excitement
            self.motion.setAngles(
                ["HeadYaw"],
                [0.1 if i % 2 == 0 else -0.1],
                0.2,
            )

            time.sleep(0.06)

            # Move OUT
            self.motion.angleInterpolationWithSpeed(names, open_pose, 0.10)

            time.sleep(0.08)

        # Finish pose
        self.motion.angleInterpolationWithSpeed(
            ["LHand", "RHand", "HeadPitch"],
            [0.7, 0.7, -0.05],
            0.2,
        )

        time.sleep(0.5)

    def goodbye(self):
        # Soft forward engagement before wave
        self.motion.angleInterpolationWithSpeed(
            ["HipPitch"],
            [-0.06],
            0.06,
        )

        # Prepare arm in a natural "ready to wave" position
        prep_names = [
            "RShoulderPitch",
            "RShoulderRoll",
            "RElbowYaw",
            "RElbowRoll",
            "RWristYaw",
            "RHand",
        ]

        prep_angles = [
            0.35,
            -0.20,
            1.10,
            1.05,
            0.10,
            1.0,
        ]

        self.motion.angleInterpolationWithSpeed(prep_names, prep_angles, 0.18)

        time.sleep(0.15)

        # Main wave motion (rhythmic + slightly varied)
        for i in range(6):
            # wave out
            self.motion.setAngles(
                ["RElbowYaw", "RWristYaw"],
                [1.25, 0.55, 0.08 if i % 2 == 0 else -0.08],
            )

            time.sleep(0.18)

            # wave in
            self.motion.setAngles(
                ["RElbowYaw", "RWristYaw"],
                [0.95, -0.25, -0.06 if i % 2 == 0 else 0.06],
            )

            time.sleep(0.18)

        # Warm finishing gesture (soft lowering + smile-like openness)
        self.motion.angleInterpolationWithSpeed(
            [
                "RShoulderPitch",
                "RElbowRoll",
                "RHand",
            ],
            [
                0.55,
                0.60,
                0.65,
            ],
            0.12,
        )

        time.sleep(1.0)
