import uvicorn
import time
import state
import requests

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pepper import speak
from tts import pop_stream_session, stream_tts_wav

PORT = 9701
CONTROLLER_URL = "http://controller:8000"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextRequest(BaseModel):
    text: str
    state_version: int


def _log_interrupt_to_controller(cleared_queue_count):
    try:
        requests.post(
            "{}/log-system-event".format(CONTROLLER_URL),
            json={
                "type": "SPEECH_INTERRUPT",
                "text": "Speech interrupted. Cleared {} queued utterance(s).".format(
                    cleared_queue_count
                ),
            },
            timeout=0.5,
        )
    except Exception as exception:
        print("Could not log speech interrupt to controller: {}".format(exception))


@app.post("/interrupt")
def interrupt_api():
    cleared_queue_count = state.queued_speech_waiters
    state.speech_cancel_generation += 1
    state.queued_speech_waiters = 0
    state.is_user_talking = False
    state.robot_is_speaking = False
    state.robot_ignore_vad_until = time.time() + 0.2
    state.robot_tts_start_time = 0.0
    state.robot_tts_pcm_16k = None

    _log_interrupt_to_controller(cleared_queue_count)

    return {"status": "ok"}


@app.post("/playback-ended")
def playback_ended_api():
    state.robot_is_speaking = False
    state.robot_ignore_vad_until = time.time() + 0.35
    state.robot_tts_start_time = 0.0
    state.robot_tts_pcm_16k = None
    return {"status": "ok"}


@app.post("/speak")
def speak_api(request: TextRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if request.state_version is not None:
        state.current_version = max(state.current_version, request.state_version)

    speak(request.text, version=request.state_version)


@app.get("/tts-stream/{token}")
def tts_stream_api(token: str):
    session = pop_stream_session(token)
    if session is None:
        raise HTTPException(status_code=404, detail="Stream session not found")

    stream_version = session.get("state_version")
    if stream_version is not None and stream_version != state.current_version:
        raise HTTPException(status_code=409, detail="Stream session is outdated")

    text = session.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Stream session has empty text")

    try:
        def _on_stream_start():
            state.robot_is_speaking = True
            state.robot_ignore_vad_until = time.time() + 0.2
            state.robot_tts_start_time = time.time()

        return StreamingResponse(
            stream_tts_wav(text, on_stream_start=_on_stream_start),
            media_type="audio/wav",
        )
    except Exception as exception:
        raise HTTPException(status_code=502, detail=str(exception))


def start_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
