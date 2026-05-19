import os

from openai import AzureOpenAI


_CLIENT = None


def _get_client() -> AzureOpenAI:
    global _CLIENT

    if _CLIENT is None:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        if not endpoint or not api_key:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set"
            )

        _CLIENT = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key,
        )

    return _CLIENT


def generate_response(prompt: str) -> str:
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-nano")
    client = _get_client()

    try:
        fallback = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "system", "content": prompt}],
        )

        message = fallback.choices[0].message.content if fallback.choices else ""
        output_text = (message or "").strip()
        if output_text:
            return output_text

    except Exception as exception:
        print(f"Exception in Azure OpenAI request: {exception}")

    return """{"text": "Oh! My circuits got a little tangled for a second there. I'm so sorry!", "movement": "lean"}"""
