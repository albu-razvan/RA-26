import json
import os
import re
import struct
import subprocess
import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

MODEL_ROOT = os.environ.get("PIPER_MODEL_ROOT", "/models")
DEFAULT_SPEAKER = os.environ.get("PIPER_SPEAKER", "androgynous")
PIPER_PATH = os.environ.get("PIPER_PATH", "piper")
LENGTH_SCALE = os.environ.get("LENGTH_SCALE", "0.72")
NOISE_SCALE = os.environ.get("NOISE_SCALE", "0.9")
NOISE_W_SCALE = os.environ.get("NOISE_W_SCALE", "0.8")


def _env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

app = FastAPI()

MAX_CONCURRENT_SYNTHESIS = int(os.environ.get("PIPER_MAX_CONCURRENT_SYNTHESIS", "1"))
SYNTHESIS_SLOT_TIMEOUT_SECONDS = float(
    os.environ.get("PIPER_SYNTHESIS_SLOT_TIMEOUT_SECONDS", "20")
)
PIPER_LOG_STDERR = _env_flag("PIPER_LOG_STDERR", default=False)
_synthesis_slots = threading.BoundedSemaphore(value=max(1, MAX_CONCURRENT_SYNTHESIS))


class StreamRequest(BaseModel):
    text: str
    speaker: str = DEFAULT_SPEAKER


def _wav_header(sample_rate, channels=1, bits_per_sample=16):
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8

    # Streamed WAV: use max placeholder sizes.
    data_size = 0x7FFFFFFF
    riff_size = 36 + data_size

    return b"".join(
        [
            b"RIFF",
            struct.pack("<I", riff_size),
            b"WAVE",
            b"fmt ",
            struct.pack(
                "<IHHIIHH",
                16,
                1,
                channels,
                sample_rate,
                byte_rate,
                block_align,
                bits_per_sample,
            ),
            b"data",
            struct.pack("<I", data_size),
        ]
    )


def _resolve_speaker_name(requested):
    candidate = (requested or "").strip() or DEFAULT_SPEAKER
    if not re.match(r"^[A-Za-z0-9_-]+$", candidate):
        return DEFAULT_SPEAKER

    model_file = os.path.join(MODEL_ROOT, candidate, "model.onnx")
    if os.path.exists(model_file):
        return candidate

    return DEFAULT_SPEAKER


def _resolve_model_paths(speaker):
    model_file = os.path.join(MODEL_ROOT, speaker, "model.onnx")
    config_file = model_file + ".json"

    if not os.path.exists(model_file):
        raise HTTPException(status_code=404, detail="Requested speaker model not found")

    return model_file, config_file


def _read_sample_rate(config_file):
    try:
        with open(config_file, "r", encoding="utf-8") as file_handle:
            config = json.load(file_handle)
            return int(config.get("audio", {}).get("sample_rate", 16000))
    except Exception:
        return 16000


def _build_piper_command(model_file, config_file):
    command = [
        PIPER_PATH,
        "-m",
        model_file,
        "--length-scale",
        LENGTH_SCALE,
        "--noise-scale",
        NOISE_SCALE,
        "--noise-w-scale",
        NOISE_W_SCALE
    ]

    if os.path.exists(config_file):
        command.extend(["-c", config_file])

    command.append("--output-raw")
    return command


@app.post("/stream")
def stream_tts(request: StreamRequest):
    text = (request.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    speaker = _resolve_speaker_name(request.speaker)
    model_file, config_file = _resolve_model_paths(speaker)
    sample_rate = _read_sample_rate(config_file)
    channels = 1

    acquired = _synthesis_slots.acquire(timeout=SYNTHESIS_SLOT_TIMEOUT_SECONDS)
    if not acquired:
        raise HTTPException(
            status_code=503,
            detail="TTS engine is busy. Could not reserve synthesis slot in time.",
        )

    process_ref = {"proc": None}

    def output_generator():
        try:
            stderr_target = subprocess.PIPE if PIPER_LOG_STDERR else subprocess.DEVNULL
            process = subprocess.Popen(
                _build_piper_command(model_file, config_file),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr_target,
                bufsize=0,
            )
            process_ref["proc"] = process

            process.stdin.write(text.encode("utf-8"))
            process.stdin.close()

            yield _wav_header(sample_rate=sample_rate, channels=channels)

            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break

                yield chunk

            return_code = process.wait(timeout=5)
            if return_code != 0:
                error_output = ""
                if process.stderr is not None:
                    error_output = process.stderr.read().decode("utf-8", errors="replace")
                print("Piper exited with non-zero code {}: {}".format(return_code, error_output))
        finally:
            process = process_ref.get("proc")
            if process is not None and process.poll() is None:
                process.terminate()

            _synthesis_slots.release()

    return StreamingResponse(output_generator(), media_type="audio/wav")
