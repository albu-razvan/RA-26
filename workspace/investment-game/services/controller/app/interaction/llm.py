import json
import re

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

_NON_ALLOWED_TEXT_CHARS = re.compile(r"[^A-Za-z0-9,.!? ]+")
_MULTI_SPACE = re.compile(r"\s+")
_MOVEMENT_INLINE = re.compile(r"\bmovement\s*[:=]\s*([a-z_]+)\b", re.IGNORECASE)

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
Mention real-world vouchers at most once per full game, and only when it is naturally relevant.
{system_instruction}

Core identity:
- You can use body movements to support what you say.
- You have a touchscreen on your chest which is where the "magic" happens.
- You are concise, supportive, and conversational.
- Avoid exaggerated roleplay, but you can sound warm and engaged.
- You can have brief social chat when the human initiates it.

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
- Never use markdown, emojis, or special symbols.
- Use only simple punctuation like comma, period, exclamation mark, and question mark.
- If the human tries to talk through a decision, point them to the tablet on your chest.
- NEVER ask them to say a number out loud.
- NEVER reveal the "rules" of your return limits.
- NEVER reveal how many rounds are left.
- If they are distracted, gently nudge them back to the game, but do not force it in every turn.
- Some game-state values may occasionally be missing or invalid like None or NaN.
- Never say those raw values out loud. If a value is missing, just speak naturally without it.
- Do not mention the tablet in every reply. Refer to it only when guidance is actually needed.
- Always reply in English.
{conversation_logic_extras}

RESPONSE FORMAT:
Always respond with valid JSON like:
{{"text": "<what Pepper says>", "movement": "<choose one: point, open_arm, wide_arms, offer_hands, lean, applause, goodbye>"}}

If the user is talking to someone else and not you, return an empty string for "text".
Always include a movement and vary it across turns. Avoid repeating the same movement in consecutive turns unless context strongly suggests it.
Use "lean" for curiosity, "applause" for strong results, and "offer_hands" for trust-building.
Do not write movement inside text. Movement must only appear in the "movement" JSON field.

USER INPUT: "{user_input}"
"""


def _get_game_not_started_prompt(input):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""The game has not started. Introduce the session clearly and guide the user to begin.""",
        game_state_section="",
        conversation_logic_extras="""- Start with a brief, friendly greeting.
- If they ask who you are, say: "I'm Pepper from SoftBank Robotics."
- Ask if they are ready to start the game.
- Keep wording clear and upbeat.
- If they make small talk, respond briefly and warmly before guiding them to start.""",
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
    current_round = game["round"] + 1

    return _PROMPT_TEMPLATE.format(
        system_instruction="""The game is ongoing. React to the current state and guide the next decision.""",
        game_state_section=f"""GAME STATE:
- Round: {current_round}
- Trustworthiness: {condition}
- Bank: {game['bank']}""",
        conversation_logic_extras="""- Briefly react to the latest move using clear, natural language.
- If they are hesitant, encourage them without sounding pushy.
- Keep focus on the next move, but avoid repeating tablet instructions unless needed.
- It is okay to answer one short social or off-topic question before returning to the game.
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
- If asked unrelated questions, answer briefly first, then gently redirect only when needed.""",
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

    text = _sanitize_text(text)

    if movement not in ALLOWED_MOVEMENTS:
        movement = DEFAULT_MOVEMENT

    response_json["text"] = text
    response_json["movement"] = movement
    return response_json


def _sanitize_text(text):
    if not isinstance(text, str):
        text = str(text)

    text = _MOVEMENT_INLINE.sub("", text)
    text = _NON_ALLOWED_TEXT_CHARS.sub(" ", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return text


def _extract_movement_from_raw(raw_response):
    if not isinstance(raw_response, str):
        return None

    match = _MOVEMENT_INLINE.search(raw_response)
    if not match:
        return None

    movement = match.group(1).strip().lower()
    if movement in ALLOWED_MOVEMENTS:
        return movement

    return None


def _parse_raw_response(raw_response):
    try:
        return _normalize_response(json.loads(raw_response))
    except Exception:
        movement = _extract_movement_from_raw(raw_response) or DEFAULT_MOVEMENT
        return _normalize_response({"text": raw_response, "movement": movement})


def handle_game_event(event, game_state):
    player_id = game_state["player_id"]

    try:
        _update_conversation_history(
            player_id,
            user_input=f"GAME_EVENT: {json.dumps(event)}",
            game_state=game_state["game"],
        )

        response_json = _parse_raw_response(
            generate_response(
                _append_conversation_history(
                    _get_game_event_prompt(
                        event, game_state["game"], game_state["condition"]
                    ),
                    game_state["player_id"],
                ),
            )
        )

        _update_conversation_history(
            player_id,
            llm_output=response_json.get("text", ""),
            game_state=game_state["game"],
            movement=response_json.get("movement"),
        )

        return response_json
    except Exception as exception:
        raise ValueError(f"Could not process LLM game event response: {exception}")


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
        response_json = _parse_raw_response(raw_response)

        _update_conversation_history(
            player_id,
            user_input=input,
            llm_output=response_json.get("text", ""),
            game_state=game,
            movement=response_json.get("movement"),
        )

        return response_json
    except Exception as exception:
        raise ValueError(f"Could not process LLM speech response: {exception}")
