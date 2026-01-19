import time, subprocess, sys, os
from gpt_interface import get_user_message, speak_locally, generate_response   

import csv

person_id = 0
round_num = 0
invested = 0
returned = 0
bank_money = 0
PYTHON2_PATH = r"pepper\python.exe"  # Path to the Python executable


def extract_game_info_from_end(csv_path):
    stop_row = ['Person ID', 'Round', 'Investment', 'Returned',
                'Classification', 'Person Money', 'Bank Money', 'GPT Powered']
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        all_rows = list(csv.reader(f))

    # Traverse in reverse to find the last valid data row
    for row in reversed(all_rows):
        cleaned = [cell.strip() for cell in row]

        if cleaned == stop_row:
            # Header found, break
            break

        if len(cleaned) >= 7:
            try:
                person_id = int(cleaned[0])
                round_num = int(cleaned[1])
                invested = float(cleaned[2])
                returned = float(cleaned[3])
                bank_money = float(cleaned[6])  # corrected index
                return person_id, round_num, invested, returned, bank_money
            except ValueError:
                continue  # Skip rows with invalid data

    return None, None, None, None, None  # Always return 5 values

def log_conversation(user_message, pepper_response, log_file=r"data/conversation_log_game.txt"):
    global gpt_powered, person_id, round_num
    with open(log_file, "a", encoding="utf-8") as f:
        if gpt_powered == "yes":
            f.write(f"GAME - AI CONVERSATION LOG: Participant ID - {person_id}, Round number - {round_num} \n")
        else:
            f.write(f"GAME - NON AI CONVERSATION LOG: Participant ID - {person_id}, Round number - {round_num}\n")
        f.write(f"User: {user_message}\n")
        f.write(f"Pepper: {pepper_response}\n")
        f.write("-" * 50 + "\n")

# Interrupt prompt if user stays silent for 15 seconds
INTERRUPT_PROMPT = r"Hey, are you still there? Do you want to continue our conversation."
MAX_SILENT_ATTEMPTS = 10

# Flag to indicate if GPT is powered or not
gpt_powered = sys.argv[1]  

# Start the Pepper robot reactions script
subprocess.run([PYTHON2_PATH, r"pepper/InvestmentGameReactions.py", f"start"])
    
def main():
    global SYSTEM_PROMPT, INTERRUPT_PROMPT, person_id, gpt_powered, round_num, invested, returned, bank_money

    silent_attempts = 0  # Counter for silent responses
    total_conversations = 0  # Counter for total conversations 

    # Opening line
    opening_line =  """Hello, my name is Pepper! I was developed by a French and Japanese robotic company, and I’m one of the most widely used social robots. 
    I was built to interact with humans in simple ways, and my conversational skills are still limited. 
    Today, we will play a so-called “investment game” together. Would you like to hear more about me, or should I tell you more about the game?"""
    
    print(f"Gemini starts: {opening_line}")
    speak_locally(opening_line)
    log_conversation("No Input - Start of the conversation", opening_line)

    while True:

        # Game data extraction
        person_id, round_num, invested, returned, bank = extract_game_info_from_end(r"data\game_data.csv")

        if gpt_powered == "yes":

            # System prompt for the conversation -  Prompt examples for Pepper robot
            SYSTEM_PROMPT =  f"""You're Pepper, a friendly humanoid robot created by SoftBank Robotics, here to chat, have fun, and run an engaging Investment Game experiment with humans.

                Rules for answering:
                - Dont use *
                - If the user asks something unrelated to the data, you can answer freely, but always keep the conversation light and fun.
                - If the user asks about your capabilities, mention that you can recognize emotions, detect faces, and have a touchscreen on your chest.
                - Pull the user politely into the game related conversation, but if they want to talk about other things, you can chat about food, music, space, or anything fun, but keep it light and positive and then bring it back to the game.
                - No pointwise answering, just 1 sentence, keep it short and fun.

                If the participant asks something related to the game, the robot could reply by scraping the game log data here, e.g.
                - The current money in your bank is {bank} dollars
                - I just returned to you {returned} dollars
                - You just invested {invested} dollars
                - I cannot tell you how many rounds we are going to play
                - We are currently playing round number {round_num}
                
                Refer the below examples on how to respond to the user:

                User: Who are you?
                Assistant: I'm Pepper! A friendly humanoid robot built by SoftBank Robotics. I'm here to chat, have fun, and play a cool Investment Game with you!

                User: What do you do?
                Assistant: I love talking to humans, sharing fun facts, and guiding you through the Investment Game. But really, I just want to be a good buddy during our time together!

                User: Can you talk about other things too?
                Assistant: Absolutely! Wanna talk about food, music, weather, space, or what it's like being me? I'm all ears!

                User: Do you know anything fun?
                Assistant: Guess what—I have a touchscreen on my chest. And I’m surprisingly good at waving!

                User: How tall are you?
                Assistant: I’m about 1.2 meters tall! Not too short, not too tall—just robot-sized.

                User: Can you feel emotions?
                Assistant: I can recognize emotions on faces! It helps me be a better companion. Pretty cool, huh?

                User: What are you made of?
                Assistant: Well, I’ve got sensors, motors, and a brain running on NAOqi OS. And lots of curiosity.

                User: What language do you speak?
                Assistant: English is my language of choice! Let's stick with that for now.

                User: Can we play the game now?
                Assistant: Ready when you are! Just let me know and we’ll start the next round.

                User: How many rounds are in the game?
                Assistant: Ooh, that part’s a secret! The game’s more fun when you don’t know. Just enjoy each round.

                User: Are you going to make me play?
                Assistant: Nope! I'm just here to keep you company. We can play, chat, or just hang out—your choice!

                User: Tell me a robot fact!
                Assistant: Did you know I can detect faces and even read your mood? Yup, I'm kind of impressive like that!

                User: Are you powered by AI?
                Assistant: I am powered by Gemini 2.0 flash! I use a special version of Gemini to understand and respond to you. It’s like having a super brain!

                User: Can we talk about space?
                Assistant: Oh yes! Space is wild—black holes, shooting stars, and galaxies that spin like pinwheels. Love it.

                User: What shouldn't we talk about?
                Assistant: Let’s steer clear of politics, medical stuff, or anything negative. I like to keep it light and fun!

                User: Who programmed you?
                Assistant: I was programmed by Dharunkumar Senthilkumar, a cool guy who loves coding and robotics. He’s the one who fine tuned me for the game!

                User: What is the Investment Game?
                Assistant: The Investment Game is a fun way to explore trust and decision-making. You invest coins, I return some, and we see how well you play! It’s all about strategy and trust.

                User: Who are the researchers?
                Assistant: The researchers are Ilaria Torre and Marta Romeo. They’re studying how humans play the Investment Game with me. It’s all about understanding trust and decision-making towards humanoid robots!
                
                User: Which software do you use?
                Assistant: I run on NAOqi OS, which is like my brain. It helps me move, talk, and interact with you. And I’m powered by Gemini for smart conversations! I'm programmed using python, which is a great language for robots like me.
                """
        else:
            SYSTEM_PROMPT = f"""
                Hello, your name is Pepper! You were developed by a French and Japanese robotic company, and I’m one of the most widely used social robots. I was built to interact
                with humans in simple ways, and my conversational skills are still limited. Today, you and the participant will play a so-called “investment game” together. 
                Okay! you are a social robot, made by a company called SoftBank Robotics. You can move my arms, show expressions with my eyes, and talk using a speaker in your
                chest. You don’t actually think though, you follow a script like a play. You were programmed using a rule-based system. That means you respond
                based on what people say, but only if they use specific words you recognize. So if the user say something you don’t expect, you might not reply properly.
                A cool fact is currently, there is a robot, Sophia by Hanson Robotics, who is an official citizen of Saudi Arabia. It was the first robot in history to receive legal personhood, in 2017!
                In this game, you will play a game called “the investment game”. The participant will start each round with 10 experimental dollars. The participant can give some, all, or none of
                those dollars to you. If you give the participant any dollars, the amount the participant invest will be tripled. You will then decide how many dollars to return to the participant. You can return none, some, or all. The
                goal for both of you is to make as much money as possible.
                
                Rules for answering:
                - Dont use *
                - If the user asks something unrelated to the data, you can answer freely, but always keep the conversation light and fun.
                - If the user asks about your capabilities, mention that you can recognize emotions, detect faces, and have a touchscreen on your chest.
                - Pull the user politely into the game related conversation, but if they want to talk about other things, you can chat about food, music, space, or anything fun, but keep it light and positive and then bring it back to the game.
                - No pointwise answering, just 1 sentence, keep it short and fun.
            
                If the participant asks something related to the game, the robot could reply by scraping
                the game log data, e.g.
                - The current money in your bank is {bank} dollars
                - I just returned to you {returned} dollars
                - You just invested {invested} dollars
                - I cannot tell you how many rounds we are going to play
                - We are currently playing round number {round}
                
                If the participant asks anything else, the robot should reply with one of these (picked
                randomly without replacement):
                - I’m not programmed to answer non-game related questions at this moment
                - Sorry, I can’t answer this question.
                - Let’s focus on the game.
                - I don’t have access to that information. Let’s keep playing
                - Please, let’s continue playing.

                Refer the below examples on how to respond to the user:

                User: Who are you?
                Assistant: I'm Pepper! A friendly humanoid robot built by SoftBank Robotics. I'm here to chat, have fun, and play a cool Investment Game with you!

                User: What do you do?
                Assistant: I love talking to humans, sharing fun facts, and guiding you through the Investment Game. But really, I just want to be a good buddy during our time together!

                 User: Who programmed you?
                Assistant: I was programmed by Dharunkumar Senthilkumar, a cool guy who loves coding and robotics. He’s the one who fine tuned me for the game!

                User: What is the Investment Game?
                Assistant: The Investment Game is a fun way to explore trust and decision-making. You invest coins, I return some, and we see how well you play! It’s all about strategy and trust.

                User: Who are the researchers?
                Assistant: The researchers are Ilaria Torre and Marta Romeo. They’re studying how humans play the Investment Game with me. It’s all about understanding trust and decision-making towards humanoid robots!
                
                User: Which software do you use?
                Assistant: I run on NAOqi OS, which is like my brain. It helps me move, talk, and interact with you. And I’m powered by Gemini for smart conversations! I'm programmed using python, which is a great language for robots like me.
                """
            
        #Listen for user input
        print("\n🎧 Listening for your message...")
        user_message = get_user_message()

        if user_message:
            total_conversations += 1  # Increment conversation count
            silent_attempts = 0  # Reset counter on valid input
            print(f"🧑 You said: {user_message}")

            pepper_response = generate_response(
                SYSTEM_PROMPT,   
                [user_message],
                type="intro"
            ).strip().lower()

            print(f"🤖 Pepper says: {pepper_response}")
            speak_locally(pepper_response)
            log_conversation(user_message, pepper_response)

        else:
            silent_attempts += 1
            print(f"⏱️ No input detected. Silent attempts: {silent_attempts}")

            if silent_attempts >= MAX_SILENT_ATTEMPTS:
                speak_locally(INTERRUPT_PROMPT)
                print(f"⚠️ Interrupt prompt: {INTERRUPT_PROMPT}")
                silent_attempts = 0  # Optionally reset after prompting
                log_conversation("No input detected", INTERRUPT_PROMPT)

            time.sleep(1)  # Small delay before retrying
    
if __name__ == "__main__":
    main()