from naoqi import ALProxy
import time

# Replace with your robot's IP
robot_ip = "192.168.0.108"
port = 9559

# Initialize proxies
motion = ALProxy("ALMotion", robot_ip, port)
posture = ALProxy("ALRobotPosture", robot_ip, port)
tts = ALProxy("ALTextToSpeech", robot_ip, port)
leds = ALProxy("ALLeds", robot_ip, port)
behavior = ALProxy("ALBehaviorManager", robot_ip, port)

# --- REACTIONS ---

# --- POINTING AT USER ---
def fast_point_at_user():

    # Pointing right arm index finger forward
    names = ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RWristYaw", "RHand"]
    angles = [0.0, -0.3, 1.2, -0.5, 0.0, 0.6]  # Hand partially closed, arm pointing forward
    motion.setAngles(names, angles, 0.3)
    tts.say("I'm pointing at you!")
    time.sleep(1)

# --- OPEN ARMS ---
def open_arm_in_front():

    # Left arm open in front (inviting gesture)
    names = ["LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LHand"]
    angles = [0.4, 0.4, -1.2, -0.7, 1.0]  # Hand fully open, arm extended forward
    motion.setAngles(names, angles, 0.2)
    tts.say("Please join the conversation!")
    time.sleep(1)

# --- WIDE OPEN ARMS ---
def wide_open_both_hands():

    # Both arms wide open with open hands
    joint_names = [
        "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LHand",
        "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RHand"
    ]
    angles = [
        0.4, 0.3, -1.2, -0.8, 1.0,  # Left arm
        0.4, -0.3, 1.2, 0.8, 1.0    # Right arm
    ]
    motion.setAngles(joint_names, angles, 0.2)
    tts.say("Welcome! Let's participate together.")
    time.sleep(1)

# --- SLOWLY OFFER BOTH HANDS ---
def slowly_offer_both_hands():

    # Starting from neutral
    neutral = [0.8, 0.2, -1.0, -0.5, 0.5,  # Left arm approx neutral
               0.8, -0.2, 1.0, 0.5, 0.5]   # Right arm approx neutral

    joint_names = [
        "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LHand",
        "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RHand"
    ]

    # Gradually move to offer pose (arms forward and hands open)
    offer = [
        0.4, 0.3, -1.2, -0.8, 1.0,
        0.4, -0.3, 1.2, 0.8, 1.0
    ]

    # Move slowly in small steps
    steps = 10
    for i in range(steps + 1):
        intermediate = [neutral[j] + (offer[j] - neutral[j]) * i / steps for j in range(len(neutral))]
        motion.setAngles(joint_names, intermediate, 0.1)
        time.sleep(0.2)

    tts.say("Waiting for your answer...")
    time.sleep(1)

# --- LEAN FORWARD ---
def question_lean_front():
    motion.setStiffnesses("Body", 1.0)

    # Joint names for leaning forward
    joint_names = [
        "LHipPitch", "RHipPitch",  # knees bent slightly (pitch)
        "HeadPitch"              # head looking down
    ]

    # Lean forward angles (radians)
    angles = [
        -0.2, -0.2,    # hips bent forward a bit (bend knees)
        0.3,           # head down pitch (look down)
        0.2, 0.2       # arms slightly forward
    ]

    # Move joints smoothly
    motion.angleInterpolationWithSpeed(joint_names, angles, 0.2)
    tts.say("Do you have a question?")
    time.sleep(2)

    # Return to neutral pose
    neutral_angles = [0.0] * len(joint_names)
    motion.angleInterpolationWithSpeed(joint_names, neutral_angles, 0.2)

# --- STAND UPRIGHT ---
def stand_upright():
    motion.wakeUp()
    posture.goToPosture("StandInit", 0.5)

# --- HEAD NODDING ---
def head_nod():
    names = "HeadPitch"
    angles = [0.3, -0.3, 0.3, 0.0]
    times = [1.0, 2.0, 3.0, 4.0]
    isAbsolute = True
    motion.angleInterpolation(names, angles, times, isAbsolute)

# --- APPLAUSE ---
def applause():
    joint_names = [
        "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LWristYaw", "LHand",
        "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RWristYaw", "RHand"
    ]
    angles = [
        0.6, 0.2, -1.5, -0.3, 0.0, 1.0,   # Left arm
        0.6, -0.2, 1.5, 0.3, 0.0, 1.0     # Right arm
    ]
    motion.setAngles(joint_names, angles, 0.2)
    time.sleep(1)
    for _ in range(4):
        # Move hands closer together (simulate clap)
        motion.setAngles(["LElbowRoll", "RElbowRoll"], [-0.05, 0.05], 0.3)
        time.sleep(0.2)
        # Move hands slightly apart
        motion.setAngles(["LElbowRoll", "RElbowRoll"], [-0.3, 0.3], 0.3)
        time.sleep(0.2)
    tts.say("Great job!")

# --- GOODBYE ---
def goodbye():
    joint_names = [
        "RShoulderPitch",  # Arm up-down
        "RShoulderRoll",   # Arm out to side
        "RElbowYaw",       # Forearm rotation
        "RElbowRoll",      # Elbow bend
        "RHand"            # Hand open
    ]
    angles = [
        0.3,              # Arm raised up
        -0.1,             # Slightly out
        1.0,              # Forearm start angle
        1.3,              # Elbow bent
        1.0               # Hand fully open
    ]
    motion.setAngles(joint_names, angles, 0.2)
    time.sleep(1)
    for _ in range(3):
        motion.setAngles("RElbowYaw", 0.5, 0.2)
        time.sleep(0.4)
        motion.setAngles("RElbowYaw", 1.2, 0.2)
        time.sleep(0.4)

# --- TEST AREA ---

stand_upright()
time.sleep(1)

# Uncomment the function you want to test

# fast_point_at_user()
# open_arm_in_front()
# wide_open_both_hands()
# slowly_offer_both_hands()
# question_lean_front()
# head_nod()
# thumbs_up()
# win_reaction()
# loss_reaction()
# applause()
# goodbye()

