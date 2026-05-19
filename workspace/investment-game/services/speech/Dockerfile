FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg build-essential portaudio19-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 torchaudio==2.5.1 && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "app.py"]
