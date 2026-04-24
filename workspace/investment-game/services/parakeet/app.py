import uvicorn
from fastapi import FastAPI, UploadFile
import onnx_asr
import tempfile
import soundfile as sf
import numpy as np

app = FastAPI()
model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3")


@app.post("/transcribe")
async def transcribe(file: UploadFile):
    audio_data = None
    temp_file = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            temp_file = tmp.name
            content = await file.read()
            tmp.write(content)

        audio_data, _ = sf.read(temp_file)

        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        audio_data = audio_data.astype(np.float32)

        text = model.recognize(audio_data)

        return {"text": text.strip()}

    except Exception as e:
        print(f"Transcription error: {e}")
        return {"text": ""}

    finally:
        if temp_file:
            try:
                import os
                os.remove(temp_file)
            except:
                pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9600)