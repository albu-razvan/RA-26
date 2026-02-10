from fastapi import FastAPI, UploadFile
from faster_whisper import WhisperModel
import numpy as np
import soundfile as sf

app = FastAPI()
model = WhisperModel("base.en", device="cpu", compute_type="int8")


@app.post("/transcribe")
async def transcribe(file: UploadFile):
    audio_data, _ = sf.read(file.file)

    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)
    audio_data = audio_data.astype(np.float32)

    segments, _ = model.transcribe(audio_data, beam_size=5)

    text = "".join([segment.text for segment in segments])
    return {"text": text.strip()}
