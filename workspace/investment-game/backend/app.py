# -*- coding: utf-8 -*-

"""
This is a Flask web application that simulates an investment game.
The app allows users to invest initial_money and receive returns based on a normal distribution.    

Author: Dharunkumar Senthilkumar    
Date: 2023-10-03
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import time, sys, os, csv, subprocess, random, threading
import numpy as np
from waitress import serve
from gpt.gpt_interface import speak_locally

# Initialize global variables
# These variables are used to store the state of the application and the user's data.
# They are initialized to default values and will be updated as the user interacts with the app.
bank = 0
person_id = 0
round_num = 0
investment = 0
returned = 0
classification = "Trustful" # Default classification is "Trustful"
initial_money = 0 # Default initial_money is 0
gpt_powered = sys.argv[1]  # Default value is "not". It can be set to "yes" if the app is powered by GPT.
trust = sys.argv[2]  # Default trust value is 'T' (Trustworthy)
PYTHON2_PATH = r"pepper\python.exe"  # Path to the Python executable

# Global variables for threading and stopping
current_thread = None
stop_event = None

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Non AI dialogues to speak at the start of each round

non_ai_dialogues = [
    "Remember, there is potential for earning, if we both trust each other",
    "In my opinion, we should keep co-operating until the end",
    "Look at how fast the total money in the bank is growing!",
    " I will demonstrate that you can trust me, just as I trust you",
    " I think we can do better. Let’s try our best to get the bank growing",
    " If we both invest in each other, the final reward will be bigger",
    " I think we can definitely go home with much more money than this",
    " I have thought of a strategy, I hope it will work",
    " You have to trust me. I have every intention to repay your trust",
    " There is no point in keeping the money hidden under the mattress",
    " I trust you, and I will show you that you can trust me as well",
    " If I keep all your investment, you will not invest anymore",
    " Even if I return part of your investment, I will make a profit"
    " As long as co-operation continues, I’m happy to earn a bit less",
    " Don’t forget that we will make more money if we both share what we get",
    " The more money you invest, the more money the two of us will earn",
    " The goal of the game is to earn as much money as possible",
    " The only way to earn is by always co-operating and investing",
    " I think we should try our best to share the money we are given",
    " Let’s keep cooperating, and we will both benefit from this",
    " We should trust each other, and we will be rewarded at the end",
    "I’m not going to keep your money, this won’t help me in the long run",
    "We can earn more money than this, if we co-operate until the end",
    "There is no better tactic than to keep investing and returning"
]

# CSV file path
# This file is used to store the results of the investment rounds. Each row in the CSV file corresponds to a round of investment and contains the relevant data.
CSV_FILE = "data\game_data.csv"    

# Create CSV file with headers if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Person ID", "Round", "Investment", "Returned", "Classification", 'Person initial_Money', 'Bank initial_Money', 'GPT Powered'])

# Function to simulate a return based on a normal distribution
def normal_random(investment):
    """
    Simulates a return based on a normal distribution.
    
    Parameters:
    - investment: float, the mean of the distribution
    - trust: 1 for trustworthy (returns > investment), 0 for untrustworthy (returns < investment)
    - std_dev: standard deviation of the distribution
    
    Returns:
    - float: simulated return value
    """
    global trust

    trust = 'T' # T for trustworthy, U for untrustworthy
    std_dev = 0.5
    max_return = 3 * investment
    min_return = 0

    while True:
        value = np.random.normal(loc=investment, scale=std_dev * investment)

        if trust == 'T' and investment < value <= max_return:
            return round(value)
        elif trust == 'U' and min_return <= value < investment:
            return round(value)

@app.route('/')
def index():    
    """ Main page of the app. """

    subprocess.run([PYTHON2_PATH, r"pepper/InvestmentGameReactions.py", f"start"])
    
    return render_template('index.html')

@app.route('/invest_page')
def invest_page():
    """ Investment page of the app. """
    global gpt_powered, non_ai_dialogues
    
    if gpt_powered == "not":
        speak_locally(random.choice(non_ai_dialogues))
    subprocess.run([PYTHON2_PATH, r"pepper/InvestmentGameReactions.py", f"invest"])
    
    return render_template('invest_page.html')

@app.route('/thinking_page')
def thinking_page():
    """ Thinking page of the app. """

    subprocess.run([PYTHON2_PATH, r"pepper/InvestmentGameReactions.py", f"think"])
    
    return render_template('thinking_page.html')

last_behavior_call = 0
@app.route('/results_page')
def results_page():
    global last_behavior_call, classification, bank, investment, returned, round_num

    now = time.time()
    if now - last_behavior_call < 5:  # 5 seconds cooldown
        print("Skipping repeated behavior call")
    else:
        last_behavior_call = now
        status = "w" if classification == "Trustful" else "l"
        subprocess.run([
            PYTHON2_PATH,
            r"pepper/InvestmentGameReactions.py",
            f"r{status}"
        ])

    return render_template(
        'results_page.html',
        round_num=round_num,
        investment=investment,
        returned=returned,
        bank=bank
    )

@app.route('/completion_page')
def completion_page():
    """ Completion page of the app. """
    global bank, round_num

    subprocess.run([PYTHON2_PATH, r"pepper/InvestmentGameReactions.py", f"final"])

    bank = 0
    return render_template('completion_page.html', final_bank=bank, final_round=round_num)


@app.route('/invest', methods=['POST'])
def invest():
    """ Endpoint to handle investment data. """
    """ This endpoint receives investment data from the client, simulates a return amount, and saves the data to a CSV file. """
    global bank, person_id, round_num, investment, returned, classification, initial_money
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data received"}), 400

    person_id = int(data.get('person_id'))
    round_num = int(data.get('round'))
    investment = int(data.get('investment'))

    if None in (person_id, round_num, investment):
        return jsonify({"error": "Missing required fields"}), 400

    # Simulate a return amount
    returned = normal_random(investment)
    classification = "Trustful" if returned >= investment else "Untrustful"

    # Calculate new balances
    initial_money = 10
    bank += initial_money - investment + returned

    # Save to CSV
    with open(CSV_FILE, "a", newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            person_id, round_num, investment, 
            returned, classification, initial_money, bank, gpt_powered
        ])

    return jsonify({
        "person_id": person_id,
        "round": round_num,
        "investment": investment,
        "returned": returned,
        "classification": classification,
        "initial_money": initial_money,
        "bank": bank
    })

# Function to run the Flask server (prod-ready)
def run_flask():
    serve(app, host='127.0.0.1', port=1234)

# Run Electron app from its folder
def run_electron():
    subprocess.Popen(
        ["npx", "electron", "."],
        cwd="web-app-loader",  # This is key: run Electron from this folder
        shell=True
    )

if __name__ == '__main__':
    """ Main function to run the Flask app. """
    """ This function initializes the Flask app and the GPT communication thread. """

    # Start the Flask app
    threading.Thread(target=run_flask).start()
    time.sleep(2)  # optional delay to ensure Flask is ready
    run_electron()

    subprocess.run(["python","gpt/conversation_loop.py", gpt_powered])
