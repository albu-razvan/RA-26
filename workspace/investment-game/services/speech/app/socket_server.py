import os
import threading

from audio_pipeline.constants import (
    OSD_MAX_GAIN,
    OSD_MIN_OVERLAP_TOTAL_S,
    OSD_RESIDUAL_BOOST,
    OSD_TEMPLATE_LAG_STEP_MS,
    OSD_USE_DENOISE,
    OVERLAP_LAG_OFFSETS_MS,
    SAMPLE_RATE,
)
from audio_pipeline.mic_server import MicServer
from audio_pipeline.osd_detector import OSDDetector
from audio_pipeline.processor import AudioProcessor
from audio_pipeline.realtime_stt import RealtimeSpeechTranscriber

from speech import process_speech
from pepper import speak
from service_clients import get_controller_status, is_game_not_started


def _build_osd_detector():
    try:
        return OSDDetector(
            hf_token=os.environ.get("HF_TOKEN"),
            sample_rate=SAMPLE_RATE,
            lag_offsets_ms=OVERLAP_LAG_OFFSETS_MS,
            residual_boost=OSD_RESIDUAL_BOOST,
            max_gain=OSD_MAX_GAIN,
            lag_step_ms=OSD_TEMPLATE_LAG_STEP_MS,
            use_denoise=OSD_USE_DENOISE,
            min_overlap_total_s=OSD_MIN_OVERLAP_TOTAL_S,
        )
    except Exception as exception:
        print("[OSD] Failed to load pipeline: {}".format(exception))
        return None
    


def handle_recognized_speech(text, state_version):
    status = get_controller_status(timeout=1)
    if is_game_not_started(status):
        print("Game has not started. Dropping recognized speech.")
        return

    if status.get("state_version", 0) != state_version:
        print("Game state changed before processing speech. Dropping input.")
        return

    response = process_speech(text, state_version)
    if response is None:
        return

    status = get_controller_status(timeout=1)
    if is_game_not_started(status):
        print("Game has not started. Dropping speech response.")
        return

    if status.get("state_version", 0) != state_version:
        print("Game state changed while generating speech. Dropping response.")
        return

    speak(response, version=state_version)


def start_sock_server():
    stt_transcriber = RealtimeSpeechTranscriber(
        sample_rate=SAMPLE_RATE,
        success_handler=handle_recognized_speech,
    )

    osd_detector = _build_osd_detector()
    processor = AudioProcessor(osd_detector, stt_transcriber)
    mic_server = MicServer(processor)

    threading.Thread(target=mic_server.start, daemon=True).start()

    print("[MAIN] Mic server started")
    while True:
        threading.Event().wait()
