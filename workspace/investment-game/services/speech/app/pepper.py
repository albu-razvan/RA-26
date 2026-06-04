import state
import requests
import time

PEPPER_API_URL = "http://pepper:8080"

from tts import register_stream_session, get_public_stream_url


def _start_stream_playback(stream_url):
    response = requests.post(
        "{}/play-stream".format(PEPPER_API_URL),
        json={"url": stream_url},
        timeout=2,
    )
    response.raise_for_status()


def _wait_for_turn_to_speak(text, version):
    if not state.is_user_talking and not state.robot_is_speaking:
        return True

    print("Speech busy. Queueing speech: '{}'".format(text))
    wait_started = time.time()
    queued_generation = state.speech_cancel_generation
    state.queued_speech_waiters += 1

    try:
        while state.is_user_talking or state.robot_is_speaking:
            if queued_generation != state.speech_cancel_generation:
                print("Discarding queued speech after interrupt: '{}'".format(text))
                return False

            if version is not None and version != state.current_version:
                print("Discarding queued speech (version updated while waiting): {}".format(text))
                return False

            # Safety valve in case playback-ended/interrupt callback is missed.
            if time.time() - wait_started > 10:
                print("Queued speech timed out waiting for turn: '{}'".format(text))
                return False

            time.sleep(0.1)

        # If interrupt happened exactly while busy flags were being cleared,
        # cancel queued speech instead of letting it play next.
        if queued_generation != state.speech_cancel_generation:
            print("Discarding queued speech after interrupt: '{}'".format(text))
            return False

        return True
    finally:
        if state.queued_speech_waiters > 0:
            state.queued_speech_waiters -= 1


def speak(text, version=None):
    if version is not None and version != state.current_version:
        print(f"Discarding speech (outdated before start): {text}")
        return

    if not _wait_for_turn_to_speak(text, version):
        return

    if version is not None and version != state.current_version:
        print(f"Discarding speech (outdated after waiting): {text}")
        return

    if text is None or text == "":
        return

    token = register_stream_session(text, version)
    stream_url = get_public_stream_url(token)
    if not stream_url:
        print("SPEECH_PUBLIC_HOST/COMPUTER_IP is not configured. Cannot stream TTS.")
        return

    state.robot_tts_pcm_16k = None
    state.robot_is_speaking = True
    state.robot_ignore_vad_until = time.time() + 1.2
    state.robot_tts_start_time = time.time()

    try:
        max_attempts = 3
        for attempt in range(max_attempts):
            if version is not None and version != state.current_version:
                print("Discarding speech (outdated while waiting to start): {}".format(text))
                return

            try:
                _start_stream_playback(stream_url)
                print("Started streamed TTS playback: '{}'".format(stream_url))
                return
            except requests.HTTPError as exception:
                status_code = exception.response.status_code if exception.response else None
                if status_code != 409 or attempt == max_attempts - 1:
                    raise

                # Pepper still speaking; wait for playback-ended and retry.
                time.sleep(0.25)
    except Exception as exception:
        state.robot_is_speaking = False
        state.robot_ignore_vad_until = 0.0
        print("Failed to start streamed playback: {}".format(exception))
