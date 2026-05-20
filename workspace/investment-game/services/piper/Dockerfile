FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    build-essential \
    libespeak-ng-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    piper-tts

WORKDIR /app

COPY ./app /app

ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]
