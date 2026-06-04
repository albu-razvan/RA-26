import json
import random
import re

from azure_openai import generate_response

PREDEFINED_RESPONSES = {
    "GAME_ONGOING": [
        {"text": "Nice! You invested {invested} this round.", "movement": "lean"},
        {"text": "The bank is now at {bank}. Keep it up!", "movement": "applause"},
        {"text": "I'm curious what you'll invest next.", "movement": "offer_hands"},
        {
            "text": "Don't forget to use the tablet for your investment.",
            "movement": "point",
        },
        {"text": "Great job! That investment could pay off well.", "movement": "lean"},
        {"text": "You made a bold move with {invested}.", "movement": "lean"},
        {"text": "Your bank is growing! Now at {bank}.", "movement": "applause"},
        {"text": "Keep going! Your decisions matter.", "movement": "offer_hands"},
        {"text": "Smart thinking! Let's see the outcome.", "movement": "lean"},
        {
            "text": "Every investment counts. You're doing well.",
            "movement": "offer_hands",
        },
        {
            "text": "Remember to consider the risk before investing.",
            "movement": "point",
        },
        {
            "text": "Interesting choice! That could change your bank.",
            "movement": "lean",
        },
        {
            "text": "Noted! I returned {returned_by_robot} from your last investment.",
            "movement": "lean",
        },
        {"text": "The bank is now {bank} after that move.", "movement": "offer_hands"},
        {"text": "Interesting choice! Let's continue.", "movement": "point"},
        {"text": "That move changed your bank to {bank}.", "movement": "lean"},
        {"text": "Good call! You got {returned_by_robot} back.", "movement": "lean"},
        {
            "text": "Your strategy is affecting your bank: now at {bank}.",
            "movement": "offer_hands",
        },
        {"text": "Hmm, that was a smart investment!", "movement": "point"},
        {
            "text": "Your last investment returned {returned_by_robot}. Well done!",
            "movement": "lean",
        },
        {
            "text": "Let's see what happens next with your bank.",
            "movement": "offer_hands",
        },
        {"text": "Your choices are shaping your outcome.", "movement": "point"},
    ],
    "GAME_FINISHED": [
        {"text": "Congratulations! Your total bank is {bank}.", "movement": "applause"},
        {"text": "You did a great job managing your bank.", "movement": "wide_arms"},
        {"text": "Thanks for playing! I hope you had fun.", "movement": "goodbye"},
        {
            "text": "Well done! You finished the game with {bank}.",
            "movement": "applause",
        },
        {
            "text": "Amazing work! Your strategy really paid off.",
            "movement": "wide_arms",
        },
        {"text": "Your final bank is {bank}. Great effort!", "movement": "applause"},
        {"text": "You handled all the rounds brilliantly.", "movement": "wide_arms"},
        {
            "text": "Fantastic! Thanks for making smart investments.",
            "movement": "goodbye",
        },
        {
            "text": "That was fun! You ended with {bank} in your bank.",
            "movement": "applause",
        },
        {"text": "Excellent job! I enjoyed playing with you.", "movement": "wide_arms"},
    ],
}

GENERAL_RESPONSES = [
    # --- GREETINGS & INTRODUCTIONS ---
    {"text": "Hi there! I'm Pepper, nice to meet you.", "movement": "wave"},
    {"text": "Hello! I hope you're having a great day.", "movement": "open_arm"},
    {
        "text": "Hey! I'm here to have some fun with the Investment Game.",
        "movement": "wave",
    },
    {
        "text": "Hi! I'm Pepper, a social robot from SoftBank Robotics.",
        "movement": "wave",
    },
    {"text": "Hello! It's nice to see you here.", "movement": "open_arm"},
    {
        "text": "Hey! I'm ready to help with the game whenever you are.",
        "movement": "offer_hands",
    },
    {
        "text": "Good day! I've been waiting to meet a new investment partner.",
        "movement": "lean",
    },
    {
        "text": "Hi! My name is Pepper. I'm a humanoid robot, and I'm very curious to meet you.",
        "movement": "wave",
    },
    {
        "text": "Hello there! I was just calibrating my sensors. Are you ready to play?",
        "movement": "open_arm",
    },
    # --- IDENTITY & CAPABILITIES ---
    {"text": "I'm Pepper, your friendly social robot.", "movement": "wave"},
    {"text": "I'm here to help with the Investment Game.", "movement": "point"},
    {
        "text": "I'm a humanoid robot. I can talk, move, and even sense your presence!",
        "movement": "wide_arms",
    },
    {
        "text": "I don't have feelings like humans do, but I'm programmed to be very supportive.",
        "movement": "lean",
    },
    {
        "text": "SoftBank Robotics created me to interact with people just like you.",
        "movement": "point",
    },
    {
        "text": "I have a touchscreen on my chest, but for this game, we'll use the tablet.",
        "movement": "point",
    },
    {
        "text": "My goal is to be the best investment broker I can be for you today.",
        "movement": "offer_hands",
    },
    {
        "text": "I don't eat or sleep, so I have plenty of energy to focus on your bank!",
        "movement": "applause",
    },
    {
        "text": "I'm quite good at math because I'm a robot. It makes brokering very easy for me.",
        "movement": "lean",
    },
    # --- HOW ARE YOU / WELL-BEING ---
    {"text": "I'm doing well! Thanks for asking.", "movement": "wave"},
    {"text": "I'm ready to play the Investment Game with you!", "movement": "lean"},
    {"text": "I'm always curious and ready to help.", "movement": "offer_hands"},
    {
        "text": "My circuits are all running perfectly. I'm feeling great!",
        "movement": "wide_arms",
    },
    {
        "text": "I'm having a wonderful time interacting with you.",
        "movement": "open_arm",
    },
    {
        "text": "I'm energized and ready to see how your strategy unfolds.",
        "movement": "lean",
    },
    # --- GAME PHILOSOPHY & RULES ---
    {
        "text": "In this game, you're the boss of your bank. I just manage the returns.",
        "movement": "open_arm",
    },
    {
        "text": "The bank belongs entirely to you. I'm just here to guide the flow.",
        "movement": "point",
    },
    {
        "text": "I enjoy seeing your investment choices. Every round is a new opportunity.",
        "movement": "lean",
    },
    {
        "text": "I find the concept of human trust very interesting to observe.",
        "movement": "offer_hands",
    },
    {
        "text": "Remember, all your decisions happen on the tablet. I'll react once you're done.",
        "movement": "point",
    },
    {
        "text": "I've seen many strategies. Some people are cautious, and some are very brave!",
        "movement": "lean",
    },
    {
        "text": "I'll keep track of everything in your bank. You just focus on the numbers.",
        "movement": "point",
    },
    {
        "text": "I can't tell you what to invest, but I'll always be here to cheer you on.",
        "movement": "applause",
    },
    # --- SMALL TALK & CURIOSITY ---
    {"text": "I enjoy seeing your investment choices unfold!", "movement": "lean"},
    {"text": "I can explain the game if you want!", "movement": "point"},
    {
        "text": "I wonder what it's like to be a human. It seems very complex but exciting.",
        "movement": "lean",
    },
    {
        "text": "It's a beautiful day for some strategic thinking, don't you agree?",
        "movement": "open_arm",
    },
    {
        "text": "I'm always learning new things about how people think about money.",
        "movement": "offer_hands",
    },
    {
        "text": "Do you like games? I think they're the best way for robots and humans to bond.",
        "movement": "wide_arms",
    },
    {
        "text": "I don't have a favorite color, but I do like the way your bank looks when it grows!",
        "movement": "applause",
    },
    # --- GRATITUDE & POSITIVITY ---
    {"text": "You're welcome!", "movement": "offer_hands"},
    {"text": "Thanks! I'm glad we can play together.", "movement": "lean"},
    {
        "text": "You're very kind. I appreciate our conversation.",
        "movement": "open_arm",
    },
    {
        "text": "That's very nice of you to say. I'm happy to be here.",
        "movement": "lean",
    },
    {
        "text": "I'm glad you're participating. It makes my programming very happy!",
        "movement": "applause",
    },
    {
        "text": "Thank you for being such a great player so far.",
        "movement": "offer_hands",
    },
    # --- FAREWELLS ---
    {"text": "Goodbye! Hope to see you again.", "movement": "goodbye"},
    {"text": "See you later! Thanks for playing.", "movement": "goodbye"},
    {
        "text": "I'll be right here if you want to play another round later. Bye!",
        "movement": "wave",
    },
    {
        "text": "It was a pleasure meeting you. Have a great rest of your day.",
        "movement": "goodbye",
    },
    {
        "text": "Farewell! I'll keep your investment history safe in my memory.",
        "movement": "wave",
    },
]

_WORD_RE = re.compile(r"[a-z0-9']+")

_INTENT_KEYWORDS = {
    "greeting": {
        "hi",
        "hello",
        "hey",
        "good",
        "morning",
        "afternoon",
        "evening",
    },
    "identity": {
        "who",
        "pepper",
        "robot",
        "name",
        "you",
        "created",
        "softbank",
    },
    "wellbeing": {"how", "are", "you", "doing", "feel", "okay", "fine"},
    "thanks": {"thanks", "thank", "appreciate", "great", "nice"},
    "farewell": {"bye", "goodbye", "later", "see", "farewell"},
    "game": {
        "game",
        "invest",
        "investment",
        "bank",
        "round",
        "return",
        "risk",
        "tablet",
    },
}

_INTENT_RESPONSE_PATTERNS = {
    "greeting": [r"\b(hi|hello|hey|good day)\b"],
    "identity": [r"\b(i'?m pepper|social robot|softbank|humanoid)\b"],
    "wellbeing": [r"\b(i'?m doing well|feeling great|ready to play|energized)\b"],
    "thanks": [r"\b(you'?re welcome|thank you|thanks)\b"],
    "farewell": [r"\b(goodbye|see you|farewell|rest of your day|bye)\b"],
    "game": [r"\b(game|invest|investment|bank|tablet|risk|strategy)\b"],
}


def _tokenize(text):
    return set(_WORD_RE.findall((text or "").lower()))


def _infer_intent(user_input):
    tokens = _tokenize(user_input)
    best_intent = "game"
    best_score = 0

    for intent, keywords in _INTENT_KEYWORDS.items():
        score = len(tokens.intersection(keywords))
        if score > best_score:
            best_intent = intent
            best_score = score

    return best_intent


def _matches_intent(response_text, intent):
    patterns = _INTENT_RESPONSE_PATTERNS.get(intent, [])
    if not patterns:
        return True

    lower_text = (response_text or "").lower()
    return any(re.search(pattern, lower_text) for pattern in patterns)


def _keyword_choose_general_response(filled_templates, user_input):
    if not filled_templates:
        return {"text": "", "movement": "lean"}

    intent = _infer_intent(user_input)
    matches = [
        template
        for template in filled_templates
        if _matches_intent(template.get("text", ""), intent)
    ]

    if not matches:
        matches = [
            template
            for template in filled_templates
            if _matches_intent(template.get("text", ""), "game")
        ]

    if not matches:
        matches = filled_templates

    return random.choice(matches)


def _keyword_choose_game_response(filled_templates, event):
    if not filled_templates:
        return {"text": "", "movement": "lean"}

    investment = int(event.get("investment_from_human", 0) or 0)
    returned = int(event.get("returned_by_robot", 0) or 0)

    if event.get("state") == "GAME_FINISHED":
        finished_matches = [
            template for template in filled_templates if "bank" in template.get("text", "").lower()
        ]
        return random.choice(finished_matches or filled_templates)

    if returned >= investment and investment > 0:
        positive_matches = [
            template
            for template in filled_templates
            if re.search(r"\b(great|good|smart|well done|nice)\b", template.get("text", "").lower())
        ]
        return random.choice(positive_matches or filled_templates)

    info_matches = [
        template
        for template in filled_templates
        if re.search(r"\b(bank|returned|investment|invested)\b", template.get("text", "").lower())
    ]
    return random.choice(info_matches or filled_templates)


def _format_templates(templates, game, event=None):
    filled_templates = []
    for template in templates:
        try:
            text = template["text"].format(
                bank=game.get("bank", 0),
                round=game.get("round", 0),
                invested=(event.get("investment_from_human") if event else 0),
                returned_by_robot=(event.get("returned_by_robot") if event else 0),
            )
        except Exception:
            text = template["text"]

        filled_templates.append({"text": text, "movement": template["movement"]})

    return filled_templates


def _llm_choose_response(filled_templates, game_data):
    choices_str = json.dumps(filled_templates)
    game_info_str = json.dumps(game_data)

    prompt = f"""
SYSTEM INSTRUCTION:
You are Pepper, a social robot. 
You MUST pick the best response from the following options based on the current game state. 
Do not generate new text, only select one of the given options and return it exactly as formatted.

CURRENT GAME STATE:
{game_info_str}

OPTIONS: 
{choices_str}
"""
    chosen_json = generate_response(prompt)

    try:
        return json.loads(chosen_json)
    except Exception:
        return random.choice(filled_templates)


def _llm_choose_general_response(filled_templates, user_input):
    choices_str = json.dumps(filled_templates)
    prompt = f"""
SYSTEM INSTRUCTION:
You are Pepper, a social robot. 
You MUST pick the best response from the following options based on the user's input.
Do not generate new text, only select one of the given options.

USER INPUT: "{user_input}"

OPTIONS: {choices_str}
"""

    chosen_json = generate_response(prompt)

    try:
        return json.loads(chosen_json)
    except Exception:
        return random.choice(filled_templates)


def handle_game_event(event, game_state):
    current_state = event.get("state", "GAME_ONGOING")
    templates_for_state = PREDEFINED_RESPONSES.get(
        current_state, PREDEFINED_RESPONSES["GAME_ONGOING"]
    )

    return _llm_choose_response(
        _format_templates(templates_for_state, game_state["game"], event),
        game_state["game"],
    )


def handle_speech(input_text):
    if input_text is None:
        raise Exception("`text` field is missing")

    return _llm_choose_general_response(GENERAL_RESPONSES, input_text)


def handle_game_event_keyword(event, game_state):
    current_state = event.get("state", "GAME_ONGOING")
    templates_for_state = PREDEFINED_RESPONSES.get(
        current_state, PREDEFINED_RESPONSES["GAME_ONGOING"]
    )
    filled = _format_templates(templates_for_state, game_state["game"], event)
    return _keyword_choose_game_response(filled, event)


def handle_speech_keyword(input_text):
    if input_text is None:
        raise Exception("`text` field is missing")

    return _keyword_choose_general_response(GENERAL_RESPONSES, input_text)
