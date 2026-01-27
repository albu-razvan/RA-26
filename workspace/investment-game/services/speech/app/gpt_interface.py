"""
This script connects to Pepper's Text-to-Speech (TTS) system and sends a text string to be spoken by Pepper.
It is designed to be run from the command line with the text to be spoken as an argument.
It uses the ALProxy class from the naoqi module to connect to Pepper's TTS system.
It initializes the TTS proxy with the IP address and port of Pepper's TTS system. 
It includes methods for different game reactions, such as starting the game, investing, thinking, and showing results."""

from google import genai
import speech_recognition as sr
import subprocess
import pyttsx3

# Client initialization for Google GenAI
client = genai.Client(api_key="") # Replace with your actual API key

def speak_locally(text):
    """Speaks the given text using the system speaker in a female, casual-sounding voice."""
    engine = pyttsx3.init()
    
    # Get available voices
    voices = engine.getProperty('voices')
    
    # Try to pick a female voice (adjust index or check names based on your system)
    selected_voice = None
    for voice in voices:
        if "female" in voice.name.lower() or "hazel" in voice.name.lower():
            selected_voice = voice.id
            break
    
    if selected_voice:
        engine.setProperty('voice', selected_voice)
    else:
        print("⚠️ Could not find a female voice. Using default.")
    
    # Adjust speech rate for a casual tone
    engine.setProperty('rate', 175)  # Slower is more natural (default is ~200)

    # Adjust pitch via SSML if needed (optional)
    # pyttsx3 does not support direct pitch control on Windows

    engine.say(text)
    engine.runAndWait()

def get_user_message():
    """Capture audio from the microphone and return recognized text.
       If timeout is provided, it will wait at most that many seconds for speech.
    """
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Speak now…")
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            # No speech detected within the timeout
            print("❌ Timeout — no speech detected")
            return ""
    try:
        user_message = recognizer.recognize_google(audio)
        print("📝 You said:", user_message)
        return user_message
    except sr.UnknownValueError:
        print("❌ Could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"❌ Could not request results; {e}")
        return ""

def conversation_to_prompt(conversation_history):
    lines = []
    for message in conversation_history:
        role = "User" if message["role"] == "user" else "Gemini"
        for part in message["parts"]:
            lines.append(f"{role}: {part}")
    return "\n".join(lines)

def generate_response(prompt, user_message, type = "not intro"):
    """Function to generate a response using Google GenAI."""
    """ This function uses the Google GenAI client to generate a response based on the prompt and user message. """
    # Use the Google GenAI client to generate a response
    if type != "intro":
        user_message = conversation_to_prompt(user_message)
    response = client.models.generate_content(
    model="gemini-2.0-flash", contents=[prompt, user_message]
    )
    return response.text
