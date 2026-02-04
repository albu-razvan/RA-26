FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libespeak-ng-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir piper-tts[http]

WORKDIR /app

# voices: https://rhasspy.github.io/piper-samples
RUN python3 -m piper.download_voices en_GB-semaine-medium

EXPOSE 5000

ENTRYPOINT ["python3", "-m", "piper.http_server"]
CMD ["-m", "en_GB-semaine-medium", "--host", "0.0.0.0"]