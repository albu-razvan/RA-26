from naoqi import ALProxy
import time
import sys

# NOTE: Check Pepper's IP address before running the script
ip = "192.168.0.100"
port = 9559

# Create proxies for the necessary modules
motion_proxy = ALProxy("ALMotion", ip, port)
posture_proxy = ALProxy("ALRobotPosture", ip, port)
autonomous_life_proxy = ALProxy("ALAutonomousLife", ip, port)
tts = ALProxy("ALTextToSpeech", ip, port)

# Turn off autonomouse life
autonomous_life_proxy.setState("disabled")

# Wake up the robot
motion_proxy.wakeUp()

# Set the robot to StandInit posture
posture_proxy.goToPosture("StandInit", 0.5)

time.sleep(1)

# Move forward 1 meter

if len(sys.argv) > 1:
    x = float(sys.argv[1])
else:
    x = 1.0 # meters
y = 0.0 # meters
theta = 0.0 # radians

motion_proxy.moveTo(x, y, theta)

time.sleep(2)

# tts.say("Done!")
