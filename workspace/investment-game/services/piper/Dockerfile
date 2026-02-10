FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libespeak-ng-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir piper-tts[http]

WORKDIR /app

ENTRYPOINT ["python3", "-m", "piper.http_server"]