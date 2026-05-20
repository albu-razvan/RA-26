import os
import threading
import time
import uuid

import requests

PIPER_URL = os.environ.get("PIPER_URL", "http://piper:5000/stream")
PIPER_SPEAKER = os.environ.get("PIPER_SPEAKER", "androgynous")
SPEECH_PUBLIC_HOST = os.environ.get("SPEECH_PUBLIC_HOST") or os.environ.get("COMPUTER_IP")
SPEECH_PUBLIC_PORT = int(os.environ.get("SPEECH_PUBLIC_PORT", "9701"))
STREAM_SESSION_TTL_SECONDS = float(os.environ.get("STREAM_SESSION_TTL_SECONDS", "20"))
PIPER_BUSY_RETRY_SECONDS = float(os.environ.get("PIPER_BUSY_RETRY_SECONDS", "0.2"))
PIPER_BUSY_MAX_WAIT_SECONDS = float(os.environ.get("PIPER_BUSY_MAX_WAIT_SECONDS", "8"))

_stream_sessions = {}
_stream_sessions_lock = threading.Lock()


def _cleanup_expired_sessions(now):
    expired = []
    for token, entry in _stream_sessions.items():
        if now - entry["created_at"] > STREAM_SESSION_TTL_SECONDS:
            expired.append(token)

    for token in expired:
        _stream_sessions.pop(token, None)


def register_stream_session(text, state_version):
    token = uuid.uuid4().hex
    now = time.time()

    with _stream_sessions_lock:
        _cleanup_expired_sessions(now)
        _stream_sessions[token] = {
            "text": text,
            "state_version": state_version,
            "created_at": now,
        }

    return token


def pop_stream_session(token):
    with _stream_sessions_lock:
        return _stream_sessions.pop(token, None)


def get_public_stream_url(token):
    if not SPEECH_PUBLIC_HOST:
        return None

    return "http://{}:{}/tts-stream/{}".format(
        SPEECH_PUBLIC_HOST,
        SPEECH_PUBLIC_PORT,
        token,
    )


def stream_tts_wav(text, on_stream_start=None, on_stream_end=None):
    started_wait = time.time()
    response = None

    while True:
        response = requests.post(
            PIPER_URL,
            json={"text": text, "speaker": PIPER_SPEAKER},
            stream=True,
            timeout=(3, 30),
        )

        if response.status_code != 409:
            break

        if time.time() - started_wait >= PIPER_BUSY_MAX_WAIT_SECONDS:
            response.raise_for_status()

        time.sleep(PIPER_BUSY_RETRY_SECONDS)

    response.raise_for_status()

    def iterator():
        started = False
        try:
            for chunk in response.iter_content(chunk_size=4096):
                if not chunk:
                    continue

                if not started:
                    started = True
                    if on_stream_start is not None:
                        on_stream_start()

                yield chunk
        finally:
            if on_stream_end is not None:
                on_stream_end()

    return iterator()
