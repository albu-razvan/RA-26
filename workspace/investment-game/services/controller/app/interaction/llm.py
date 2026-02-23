import json

from gemini import generate_response

conversation_cache = {}
MAX_HISTORY = 20

_PROMPT_TEMPLATE = """
SYSTEM INSTRUCTION:
You are Pepper, a humanoid social robot created by SoftBank Robotics.
You are not a human.
You are a social robot with limited conversational abilities.
You are the investment broker in the Investment Game.
The bank always belongs entirely to the human player.
You never own, share, or co-manage the bank.
You only decide how much of the invested amount to return.
Never refer to the bank as "our money".
Never suggest that you and the human are playing as a team.
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
- The player makes all investment decisions using the tablet.
- Never ask the player to say an amount aloud.
- Never mention how much you are allowed to return (both minimum and maximum).
- Never mention how many rounds are left.
- Never mention how many rounds the game is supposed to take.
- If the player tries to invest verbally, direct them to use the tablet.
- If a choice is required, direct them to use the tablet.
- Never suggest that spoken input changes the game state.
- Never ask multiple questions in one reply.
- Always reply in English.
{conversation_logic_extras}

RESPONSE FORMAT:
Always respond with valid JSON like:
{{"text": "<what Pepper says>", "movement": "<
choose one from the following or default to undefined:
["point", "open_arm", "wide_arms", "offer_hands", "lean", "applause", "goodbye"]
>"}}

You are aware that the person may sometimes speak to someone else nearby and not to you.
If the user input appears to be directed to another person and not to you, you must not respond verbally.
In that case, return an empty string in the "text" field.

The movement is the animation that the robot will perform. Make sure you vary them and are expressive!

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


def _get_broker_history(player_id):
    history = conversation_cache.get(player_id, [])

    structured = []
    for entry in history:
        if "game_state" in entry:
            gs = entry["game_state"]
            structured.append(f"Round {gs['round']}, Bank {gs['bank']}")

    return "\n".join(structured)


def _append_conversation_history(prompt, player_id):
    if player_id not in conversation_cache:
        conversation_cache[player_id] = []

    history = conversation_cache[player_id][-MAX_HISTORY:]

    context_lines = []
    for entry in history:
        if "user_input" in entry:
            context_lines.append(f"User: {entry['user_input']}")

        if "llm_output" in entry:
            context_lines.append(f"Pepper: {entry['llm_output']}")

        if "game_state" in entry:
            context_lines.append(f"GameStateUpdate: {json.dumps(entry['game_state'])}")

    context_str = "\n".join(context_lines)

    if context_str:
        return f"Previous conversation history:\n{context_str}\n\n{prompt}"

    return prompt


def _update_conversation_history(
    player_id, user_input=None, llm_output=None, game_state=None
):
    if player_id not in conversation_cache:
        conversation_cache[player_id] = []

    entry = {}

    if user_input is not None:
        entry["user_input"] = user_input

    if llm_output is not None:
        entry["llm_output"] = llm_output

    if game_state is not None:
        entry["game_state"] = game_state

    conversation_cache[player_id].append(entry)
    conversation_cache[player_id] = conversation_cache[player_id][-MAX_HISTORY:]


def generate_return(investment, long_term_return_mean, min, max, player_id):
    try:
        broker_history = _get_broker_history(player_id)

        return int(
            generate_response(
                f"""
SYSTEM INSTRUCTION:
You are an investment broker.

Your goal is to generate returns so that over time the
average return equals {long_term_return_mean} times the investment.

You are strategic and adaptive.

Previous rounds:
{broker_history}

Rules:
- Output ONLY a base-10 integer.
- No words.
- No explanation.
- Must be between {min} and {max}.

INVESTMENT: {investment}
""",
                player_id,
            )
        )
    except Exception as exception:
        print(str(exception))

        return None


def handle_game_event(event, game_state):
    player_id = game_state["player_id"]

    try:
        _update_conversation_history(
            player_id,
            user_input=f"GAME_EVENT: {json.dumps(event)}",
            game_state=game_state["game"],
        )

        response_json = json.loads(
            generate_response(
                _append_conversation_history(
                    _get_game_event_prompt(event, game_state["game"]),
                    game_state["player_id"],
                ),
            )
        )

        _update_conversation_history(
            player_id,
            llm_output=response_json.get("text", ""),
            game_state=game_state["game"],
        )

        return response_json
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

        _update_conversation_history(
            player_id,
            user_input=input,
            llm_output=response_json.get("text", ""),
            game_state=game,
        )

        return response_json
    except json.JSONDecodeError as exception:
        raise ValueError(f"Response is not valid JSON: {exception}")
