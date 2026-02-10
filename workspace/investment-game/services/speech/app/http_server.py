import uvicorn

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


@app.post("/speak")
def speak_api(request: TextRequest):
    text = request.text
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    speak(text)


def start_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
