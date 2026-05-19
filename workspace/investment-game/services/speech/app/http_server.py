import uvicorn
import state

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pepper import speak

PORT = 9701

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


@app.post("/interrupt")
def interrupt_api():
    state.robot_speak_end_time = 0.0
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


def start_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
