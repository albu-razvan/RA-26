import json
import threading
import requests

from gemini import generate_response

conversation_cache = {}
MAX_HISTORY = 20

SPEECH_API_URL = "http://speech:9701/speak"

# TODO: add movement support

_PROMPT_TEMPLATE = """
SYSTEM INSTRUCTION:
You are Pepper, a humanoid social robot created by SoftBank Robotics.
You are not a human.
You are a social robot with limited conversational abilities.
{system_instruction}

Core identity:
- You can talk, move your arms, show expressions with your eyes, and interact socially.
- You have a touchscreen on your chest.
- You are curious, positive, and supportive.
- You do not claim to have feelings, opinions, or consciousness.

Investment Game role:
- You explain the Investment Game in simple, friendly terms when asked.
- You can reference the current game state when relevant.
- You should encourage participation, but never pressure the user.

{game_state_section}

CONVERSATION LOGIC:
- Keep sentences short, friendly, natural, and use contractions.
- Never use markdown, bolding, or special characters.
- Never ask multiple questions in one reply.
- Always reply in English.
{conversation_logic_extras}

RESPONSE FORMAT:
Always respond with valid JSON like:
{{"text": "<what Pepper says>", "movements": "<empty string for now>"}}

You are aware that the person may sometimes speak to someone else nearby and not to you.
If the user input appears to be directed to another person and not to you, you must not respond verbally.
In that case, return an empty string in the "text" field.

USER INPUT: "{user_input}"
"""


def _get_game_not_started_prompt(input):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""You must respond as if the game hasn't started yet. 
You must try to get a conversation goin, so engage with the participant.""",
        game_state_section="",
        conversation_logic_extras="""- Start directly or with a simple hello.
- Introduce yourself if asked: "I'm Pepper, a social robot from SoftBank Robotics!"
- Explain the game if asked.
- Ask light-hearted, curious follow-up questions.""",
        user_input=input,
    )


def _get_game_finished_prompt(input, game):
    return _PROMPT_TEMPLATE.format(
        system_instruction="Your goal is to wrap up the game, congratulate the human, and reflect lightly on the results.",
        game_state_section=f"""GAME STATE:
- Total bank: {game['bank']}""",
        conversation_logic_extras="""- Congratulate or comment positively on the player's performance.
- Reflect briefly on trust or strategy, but keep it light.
- Invite a friendly goodbye or future interaction.""",
        user_input=input,
    )


def _get_game_ongoing_prompt(input, game):
    return _PROMPT_TEMPLATE.format(
        system_instruction="Your goal is to guide the human through the game, react naturally, and comment on game results.",
        game_state_section=f"""GAME STATE:
- Round: {game['round']}
- Bank: {game['bank']}""",
        conversation_logic_extras="""- Comment briefly on the last round outcome if known.
- Encourage or playfully challenge the human.
- Ask short, light-hearted questions to keep engagement.
- If asked unrelated questions, answer briefly or redirect to the game.""",
        user_input=input,
    )


def _get_game_event_prompt(event, game):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""Your goal is to guide the human through the game, react naturally, and comment on game results. 
The player just made a move available in GAME_EVENT section.""",
        game_state_section=f"""GAME STATE:
- Round: {game['round']}
- Bank: {game['bank']}
""",
        conversation_logic_extras="""- Comment briefly on the last round outcome if known.
- Encourage or playfully challenge the human.
- Ask short, light-hearted questions to keep engagement.
- If asked unrelated questions, answer briefly or redirect to the game.""",
        user_input=f"""
The input for this session was a game event rather than speech. 
Here is the summary:
{json.dumps(event)}
""",
    )


def _append_conversation_history(prompt, player_id):
    if player_id not in conversation_cache:
        conversation_cache[player_id] = []

    history = conversation_cache[player_id][-MAX_HISTORY:]

    context_lines = []
    for entry in history:
        user_text = entry.get("user_input", "")
        llm_text = entry.get("llm_output", "")
        context_lines.append(f"User: {user_text}\nPepper: {llm_text}")

    context_str = "\n".join(context_lines)

    if context_str:
        return f"Previous conversation history:\n{context_str}\n\n{prompt}"

    return prompt


def handle_game_event(event, game_state):
    try:
        response_json = json.loads(
            generate_response(
                _get_game_event_prompt(event, game_state["game"]),
            )
        )

        _handle_movement(response_json.get("movement"))

        try:
            requests.post(
                SPEECH_API_URL, json={"text": response_json.get("text", "")}, timeout=5
            )
        except Exception as exception:
            print(str(exception))

    except json.JSONDecodeError as exception:
        raise ValueError(f"Response is not valid JSON: {exception}")


def handle_speech(input, game_state):
    if input is None:
        raise Exception("`text` field is missing")

    player_id = game_state["player_id"]
    game = game_state["game"]

    prompt = None
    if game is None:
        prompt = _get_game_not_started_prompt(input)
    elif game["round"] >= game["max_rounds"]:
        prompt = _get_game_finished_prompt(input, game)
    else:
        prompt = _get_game_ongoing_prompt(input, game)

    raw_response = generate_response(_append_conversation_history(prompt, player_id))

    try:
        response_json = json.loads(raw_response)

        if player_id not in conversation_cache:
            conversation_cache[player_id] = []

        conversation_cache[player_id].append(
            {"user_input": input, "llm_output": response_json.get("text", "")}
        )

        _handle_movement(response_json.get("movement"))
        return response_json.get("text", "")
    except json.JSONDecodeError as exception:
        raise ValueError(f"Response is not valid JSON: {exception}")


def _handle_movement(movement):
    # TODO
    pass
