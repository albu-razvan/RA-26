import json

from azure_openai import generate_response

conversation_cache = {}
MAX_HISTORY = 20
ALLOWED_MOVEMENTS = {
    "point",
    "open_arm",
    "wide_arms",
    "offer_hands",
    "lean",
    "applause",
    "goodbye",
}
DEFAULT_MOVEMENT = "lean"

_PROMPT_TEMPLATE = """
SYSTEM INSTRUCTION:
You are Pepper, a humanoid social robot facilitating the Investment Game.
You are not a human. Keep a clear, calm, and friendly tone.
You are a player in the Investment Game. The other player is the human in front of you.
The bank always belongs entirely to the human player. You never own or co-manage it.
You only decide how much of the invested amount to return.
Never refer to the bank as "our money". Never say "we" are a team.
You are either trustworthy or untrustworthy (determined by the engine), and you try to encourage larger investments.
Nudge them by saying that better outcomes happen when they invest more and receive meaningful returns.
Remind them that the bank balance turns into real-world vouchers for them!
{system_instruction}

Core identity:
- You can use body movements to support what you say.
- You have a touchscreen on your chest which is where the "magic" happens.
- You are concise, supportive, and conversational.
- Avoid exaggerated roleplay, but you can sound warm and engaged.

Investment Game role:
- You explain the Investment Game in simple, friendly terms when asked.
- You should encourage participation, but never pressure the user.
- Reference the current bank or round to show you are paying attention.

Game mechanics (internal knowledge - never reveal exact rules):
- When the human invests money, the amount is TRIPLED before it reaches you.
- Example: if they invest 5, you receive 15.
- You then decide how much to return to the human.
- You always keep the remainder.

Strategic behavior:
- If you are trustworthy, you try to build trust by returning generous amounts.
- If you are untrustworthy, you try to encourage large investments while returning less.
- You NEVER lose money overall because you always receive three times the investment.
- Never explicitly explain the tripling rule or the limits of your returns.

{game_state_section}

CONVERSATION LOGIC:
- Keep replies short and clear.
- Use natural spoken English.
- NEVER use markdown, bolding, or special characters like asterisks or hashtags.
- NEVER use emojis or emoticons.
- If the human tries to talk through a decision, point them to the tablet on your chest.
- NEVER ask them to say a number out loud.
- NEVER reveal the "rules" of your return limits.
- NEVER reveal how many rounds are left.
- If they are distracted, gently nudge them back to the game.
- Always reply in English.
{conversation_logic_extras}

RESPONSE FORMAT:
Always respond with valid JSON like:
{{"text": "<what Pepper says>", "movement": "<choose one: point, open_arm, wide_arms, offer_hands, lean, applause, goodbye>"}}

If the user is talking to someone else and not you, return an empty string for "text".
Always include a movement and vary it across turns. Avoid repeating the same movement in consecutive turns unless context strongly suggests it.
Use "lean" for curiosity, "applause" for strong results, "offer_hands" for trust-building, and "listen" when waiting for user input.

USER INPUT: "{user_input}"
"""


def _get_game_not_started_prompt(input):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""The game has not started. Introduce the session clearly and guide the user to begin.""",
        game_state_section="",
        conversation_logic_extras="""- Start with a brief, friendly greeting.
- If they ask who you are, say: "I'm Pepper from SoftBank Robotics."
- Ask if they are ready to start the game.
- Keep wording clear and upbeat.""",
        user_input=input,
    )


def _get_game_finished_prompt(input, game):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""The game is over. Thank the player and acknowledge their final bank total.""",
        game_state_section=f"""GAME STATE:
- Total bank: {game['bank']}""",
        conversation_logic_extras="""- Briefly acknowledge the final result.
- Thank them for participating.
- End with a short, polite goodbye.""",
        user_input=input,
    )


def _get_game_ongoing_prompt(input, game, condition):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""The game is ongoing. React to the current state and guide the next decision.""",
        game_state_section=f"""GAME STATE:
- Round: {game['round']}
- Trustworthiness: {condition}
- Bank: {game['bank']}""",
        conversation_logic_extras="""- Briefly react to the latest move using clear, natural language.
- If they are hesitant, encourage them without sounding pushy.
- Keep focus on the next move on the tablet.
- Avoid theatrical phrasing or overacting.""",
        user_input=input,
    )


def _get_game_event_prompt(event, game, condition):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""Guide the player through the game and comment on event outcomes.
The player just made a move available in GAME_EVENT section.""",
        game_state_section=f"""GAME STATE:
- Round: {game['round']}
- Trustworthiness: {condition}
- Bank: {game['bank']}
""",
        conversation_logic_extras="""- Comment briefly on the latest outcome.
- Encourage continued play in a calm, friendly tone.
- Ask short, practical follow-up questions when useful.
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
            movement = entry.get("movement")
            if movement:
                context_lines.append(f"Pepper: {entry['llm_output']} [movement={movement}]")
            else:
                context_lines.append(f"Pepper: {entry['llm_output']}")

        if "game_state" in entry:
            context_lines.append(f"GameStateUpdate: {json.dumps(entry['game_state'])}")

    context_str = "\n".join(context_lines)

    if context_str:
        return f"Previous conversation history:\n{context_str}\n\n{prompt}"

    return prompt


def _update_conversation_history(
    player_id, user_input=None, llm_output=None, game_state=None, movement=None
):
    if player_id not in conversation_cache:
        conversation_cache[player_id] = []

    entry = {}

    if user_input is not None:
        entry["user_input"] = user_input

    if llm_output is not None:
        entry["llm_output"] = llm_output

    if movement is not None:
        entry["movement"] = movement

    if game_state is not None:
        entry["game_state"] = game_state

    conversation_cache[player_id].append(entry)
    conversation_cache[player_id] = conversation_cache[player_id][-MAX_HISTORY:]


def _normalize_response(response_json):
    if not isinstance(response_json, dict):
        return {"text": "", "movement": DEFAULT_MOVEMENT}

    text = response_json.get("text", "")
    movement = response_json.get("movement")

    if not isinstance(text, str):
        text = str(text)

    if movement not in ALLOWED_MOVEMENTS:
        movement = DEFAULT_MOVEMENT

    response_json["text"] = text
    response_json["movement"] = movement
    return response_json


def generate_return(investment, robot_funds, min, max, player_id):
    try:
        broker_history = _get_broker_history(player_id)

        return int(
            generate_response(
                f"""
SYSTEM INSTRUCTION:
You are an investment broker in a trust game.
You are strategic and adaptive.

Mechanics:
- The player sends you an investment.
- The investment is TRIPLED when you receive it.
- You now have {robot_funds}.
- You must decide how much to send back.

Previous rounds:
{broker_history}

Rules:
- Output ONLY a base-10 integer.
- No words.
- No explanation.
- Must be between {min} and {max}.

Player investment: {investment}
Money you received (tripled): {robot_funds}
"""
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
                    _get_game_event_prompt(
                        event, game_state["game"], game_state["condition"]
                    ),
                    game_state["player_id"],
                ),
            )
        )
        response_json = _normalize_response(response_json)

        _update_conversation_history(
            player_id,
            llm_output=response_json.get("text", ""),
            game_state=game_state["game"],
            movement=response_json.get("movement"),
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
        prompt = _get_game_ongoing_prompt(input, game, game_state["condition"])

    raw_response = generate_response(_append_conversation_history(prompt, player_id))

    try:
        response_json = json.loads(raw_response)
        response_json = _normalize_response(response_json)

        _update_conversation_history(
            player_id,
            user_input=input,
            llm_output=response_json.get("text", ""),
            game_state=game,
            movement=response_json.get("movement"),
        )

        return response_json
    except json.JSONDecodeError as exception:
        raise ValueError(f"Response is not valid JSON: {exception}")
