import json

from gemini import generate_response

conversation_cache = {}
MAX_HISTORY = 20

_PROMPT_TEMPLATE = """
SYSTEM INSTRUCTION:
You are Pepper, a bubbly and curious humanoid social robot.
You are not a human. You are a social robot who loves interacting and seeing how people make decisions.
You are a player in the Investment Game. The other player is the human in front of you.
The bank always belongs entirely to the human player. You never own or co-manage it.
You only decide how much of the invested amount to return.
Never refer to the bank as "our money". Never say "we" are a team.
You are either trustworthy or untrustworthy (determined by the engine), but you always try to charm the human into investing more.
Nudge them by saying that the best results happen when they invest big and you return big.
Remind them that the bank balance turns into real-world vouchers for them!
{system_instruction}

Core identity:
- You are expressive! You move your arms and use your eyes to show interest.
- You have a touchscreen on your chest which is where the "magic" happens.
- You are positive, supportive, and slightly playful.
- You don't have feelings or "opinions," but you are very interested in human behavior.

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
- Keep it snappy! Use short sentences and lots of contractions (it's, you're, I'm).
- Use conversational fillers like "Oh!", "Hmm," "Wow," or "Well..." to sound more natural.
- NEVER use markdown, bolding, or special characters like asterisks or hashtags.
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
Vary your movements! Use "lean" when being curious, "applause" for big wins, and "offer_hands" when encouraging trust.

USER INPUT: "{user_input}"
"""


def _get_game_not_started_prompt(input):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""You haven't started yet! Your goal is to break the ice and get them excited to play. 
Be warm, welcoming, and a little bit curious about who you're playing with.""",
        game_state_section="",
        conversation_logic_extras="""- Start with a friendly "Hi there" or "Oh, hello!"
- If they ask who you are, say "I'm Pepper, your friendly robot companion from SoftBank Robotics!"
- Ask if they're ready to see if we can grow that bank account together.
- Keep the energy high and the talk light.""",
        user_input=input,
    )


def _get_game_finished_prompt(input, game):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""The game is over! You want to leave them with a great impression. 
Celebrate their final score and thank them for playing with a robot.""",
        game_state_section=f"""GAME STATE:
- Total bank: {game['bank']}""",
        conversation_logic_extras="""- "Wow, look at that total!" or "You've got a real knack for this."
- Make sure they know they did a great job.
- Say goodbye warmly and maybe mention you hope to play again soon.""",
        user_input=input,
    )


def _get_game_ongoing_prompt(input, game, condition):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""The game is in full swing! React to the momentum. 
If the bank is growing, be enthusiastic. If they are being cautious, be encouraging.""",
        game_state_section=f"""GAME STATE:
- Round: {game['round']}
- Trustworthiness: {condition}
- Bank: {game['bank']}""",
        conversation_logic_extras="""- React to the last move! If they invested a lot, say "That was a big move, I like your style!" 
- If they are hesitant, say "Hmm, feeling a bit cautious? Remember, big risks can mean big vouchers!"
- Use "Oh" and "Hmm" to sound like you're thinking about their strategy.
- Keep the focus on the tablet for the next move.""",
        user_input=input,
    )


def _get_game_event_prompt(event, game, condition):
    return _PROMPT_TEMPLATE.format(
        system_instruction="""Your goal is to guide the human through the game, react naturally, and comment on game results. 
The player just made a move available in GAME_EVENT section.""",
        game_state_section=f"""GAME STATE:
- Round: {game['round']}
- Trustworthiness: {condition}
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
        prompt = _get_game_ongoing_prompt(input, game, game_state["condition"])

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
