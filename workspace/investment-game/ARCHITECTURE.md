# System Architecture

The Investment Game system follows a microservice architecture coordinated via Docker Compose. The structure can be modified at any time to suit any other project involving speech by changing just the Controller Service component. Here is a summary of everything:

## Core Components

### 1. Frontend (Android Tablet)

- **Role**: Player interface.
- **Path**: `./frontend/`
- **Description**: A Java-based Android app that provides the UI for the investment game. It communicates with the **Controller** via REST API to start games and submit investments. It supports a "Kiosk Mode" to prevent users from exiting the app during studies.

### 2. Controller Service

- **Role**: Control speech, replies and game flow.
- **Path**: `./services/controller/`
- **Description**: A FastAPI application that manages the game state (rounds, budget, player ID) and determines robot behavior. It uses **Gemini** to select the most appropriate social response based on the current game state or user speech.

### 3. Speech Service

- **Role**: Audio Communication Hub.
- **Path**: `./services/speech/`
- **Description**: Acts as a bridge between the Pepper robot and AI models. It runs a socket server to receive raw audio from Pepper and an HTTP server to trigger Text-to-Speech (TTS). It coordinates with the **Whisper** and **Piper** services for STT and TTS respectively.

### 4. Pepper Service & Robot Handler

- **Role**: Hardware Abstraction.
- **Path**: `./services/pepper/`
- **Description**: The `robot_handler.py` script runs directly on the Pepper robot (Python 2.7/NAOqi). It streams microphone data to the Speech service and controls physical aspects like eye LED colors and animations (e.g., "thinking" pulses or "listening" states).

### 5. AI Model Services (Whisper & Piper)

- **Whisper**: A dedicated service running `faster-whisper` for near-real-time transcription of player speech.
- **Piper**: A fast, local TTS engine that generates audio files for Pepper to play back, ensuring low-latency verbal responses.

## Data Flow

1.  **Investment Flow**: Tablet (Frontend) -> Controller (Logic) -> Piper (TTS) -> Pepper (Physical Reaction/Speech)
2.  **Speech Flow**: Pepper (Mic) -> Speech Service -> Whisper (STT) -> Controller (LLM Logic) -> Speech Service -> Piper (TTS) -> Pepper (Physical Reaction/Speech)
3.  **Visual Flow**: Controller (State) -> Pepper (LEDs/Animations)

## Network Ports

| Service        | Port     | Use Case                                    |
| :------------- | :------- | :------------------------------------------ |
| **Controller** | 8000     | REST API for Frontend and Speech service.   |
| **Speech**     | 9700     | Socket for raw audio streaming from Pepper. |
| **Speech**     | 9701     | HTTP for triggering TTS responses.          |
| **Whisper**    | Internal | gRPC/HTTP for transcription requests.       |
| **Piper**      | Internal | HTTP for generating speech audio from text. |
| **Pepper**     | Internal | REST API robot interactions.                |
