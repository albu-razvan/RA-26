# -*- coding: utf-8 -*-

"""
This script connects to Pepper's Text-to-Speech (TTS) system and sends a text string to be spoken by Pepper.    
Arguments:
- The script expects a single argument: the text to be spoken by Pepper.
    - If no argument is provided, it will print an error message and exit.
    - The script uses the ALProxy class from the naoqi module to connect to Pepper's TTS system.
    - The TTS proxy is initialized with the IP address and port of Pepper's TTS system.
    
Additional functionality:
- The script includes methods for different game reactions, such as starting the game, investing, thinking, and showing results.
- Each method is designed to handle specific reactions and interactions with the user.

"""


from naoqi import ALProxy
import sys
import basic_movements as bm    
import time

class InvestmentGameReactions:
    def __init__(self, robot_ip, port=9559):
        # Initialize proxies for Pepper's modules
        self.robot_ip = robot_ip
        self.port = port
        self.tts = ALProxy("ALTextToSpeech", robot_ip, port)
        self.motion = ALProxy("ALMotion", robot_ip, port)
        self.leds = ALProxy("ALLeds", robot_ip, port) 
        self.behavior_manager = ALProxy("ALBehaviorManager", robot_ip, port)
        #self.autonomous_life = ALProxy("ALAutonomousLife", robot_ip, port)
        self.posture = ALProxy("ALRobotPosture", robot_ip, port)
        self.reset_state()

    def reset_state(self):
        try:
            # Stop all running behaviors
            for behavior in self.behavior_manager.getRunningBehaviors():
                try:
                    self.behavior_manager.stopBehavior(behavior)
                except Exception as e:
                    print "[Reset] Couldn't stop behavior {}: {}".format(behavior, str(e))
        except Exception as e:
            print "[Reset] Couldn't get running behaviors: {}".format(str(e))

        try:
            self.motion.stopMove()
        except Exception as e:
            print "[Reset] No movement to stop: {}".format(str(e))

        try:
            # Set stiffness
            self.motion.setStiffnesses("Body", 1.0)

            # Reset posture to StandInit (neutral standing)
            self.posture.goToPosture("StandInit", 0.5)
        except Exception as e:
            print "[Reset] Posture error: {}".format(str(e))

        try:
            # Set face LEDs to white
            self.leds.fadeRGB("FaceLeds", 0xFFFFFF, 0.2)
        except Exception as e:
            print "[Reset] LED reset failed: {}".format(str(e))

        #try:
        #    desired_state = "solitary" # or "interactive" or "disabled" or "safeguard" or "solitary"
        #    if self.autonomous_life.getState() != desired_state:
        #       self.autonomous_life.setState(desired_state)
        #except RuntimeError as e:
        #    print "[Start] Autonomous Life state error: {}".format(str(e))


    def start_game_reaction(self):
        self.reset_state()

        try:
            self.leds.fadeRGB("FaceLeds", 0x00FF00, 0.5)
            self.behavior_manager.runBehavior("dialog_move/animations/Nao/Standing/Wave01")
            #self.tts.say("Welcome to the investment game! Get ready to make some smart moves!")
        except Exception as e:
            print "[Start] Action error: {}".format(str(e))


    def invest_reaction(self):
        self.reset_state()
        try:
            bm.head_nod()
            time.sleep(0.3)
            self.leds.fadeRGB("FaceLeds", 0xFFFF00, 0.5)
            #self.tts.say("You will invest wisely. Let's hope it pays off!")
        except Exception as e:
            print "[Invest] Error: {}".format(str(e))

        self.reset_state()


    def thinking_action(self):
        self.reset_state()
        try:
            bm.head_nod()
            #self.tts.say("Hmm, let me calculate your returns...")
        except Exception as e:
            print "[Thinking] Error: {}".format(str(e))

        self.reset_state()

    def result_reaction(self, outcome):
        self.reset_state()

        reactions = {
            "w": {
                "text": "Great news! Your investment pays off!",
                "color": 0x00FF00,
                "behavior": "animations/Stand/Emotions/Positive/Happy_3"
            },
            "l": {
                "text": "Oh no, the market crashed!",
                "color": 0xFF0000,
                "behavior": "animations/Stand/Emotions/Negative/Sad_2"
            }
        }

        if outcome not in reactions:
            print "[Result] Invalid outcome: {}".format(outcome)
            return

        reaction = reactions[outcome]
        try:
            #self.tts.say(reaction["text"])
            time.sleep(0.2)
            self.leds.fadeRGB("FaceLeds", reaction["color"], 0.5)

            behavior = reaction["behavior"]
            if self.behavior_manager.isBehaviorInstalled(behavior):
                self.behavior_manager.startBehavior(behavior)
                time.sleep(3)
                self.behavior_manager.stopBehavior(behavior)
        except Exception as e:
            print "[Result] Error: {}".format(str(e))

        self.reset_state()

    # Final Completion Function
    def final_completion_reaction(self):
        
        self.reset_state()

        # Applause and Goodbye (custom motions)
        bm.applause()
        time.sleep(0.5)
        #bm.goodbye()

        self.reset_state()

if __name__ == "__main__":
    robot_ip = "192.168.0.108"  # Replace with your Pepper's IP address

    pepper_game = InvestmentGameReactions(robot_ip)
    func_call = sys.argv[1]

    # Call the appropriate function based on the received text
    # Test the reactions step-by-step
    if func_call == "start":
        pepper_game.start_game_reaction()
    elif func_call == "invest":
        pepper_game.invest_reaction()  
    elif func_call == "think":
        pepper_game.thinking_action()
    elif func_call[0] == "r":
        pepper_game.result_reaction(func_call[1])
    elif func_call == "final":
        pepper_game.final_completion_reaction()  
