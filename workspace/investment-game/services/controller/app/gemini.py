from google import genai
import os


def generate_response(prompt: str) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model_id = "gemini-2.5-flash-lite"

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
        )

        return response.text

    except Exception as exception:
        print(f"Exception in LLM request: {str(exception)}")

        return """{"text": "Oh! My circuits got a little tangled for a second there. I'm so sorry! Let's try that again on my tablet.", "movement": "lean"}"""
