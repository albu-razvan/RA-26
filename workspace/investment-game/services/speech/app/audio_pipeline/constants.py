import os


def _env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# Mic TCP server bind settings (Pepper streams mic PCM here).
HOST = "0.0.0.0"
PORT_MIC = 9702

# Front-mic PCM format (16kHz, mono, 16-bit) and frame sizing used by VAD.
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 20
FRAME_SIZE_BYTES = int(SAMPLE_RATE * (FRAME_DURATION_MS / 1000.0) * 2)

# Number of consecutive non-speech frames required to close an utterance.
SILENCE_LIMIT_FRAMES = int(os.environ.get("SILENCE_LIMIT_FRAMES", "55"))
# Minimum RMS energy for a frame to count as speech after VAD says "voice".
RMS_THRESHOLD = 500
# Frames of confirmed speech required to start an utterance.
SPEECH_START_THRESHOLD = 4
# Pre-roll ring buffer length (frames) appended to utterance start.
RING_BUFFER_FRAMES = 20
# Minimum utterance size; shorter captures are dropped as noise.
MIN_UTTERANCE_BYTES = 8000

# OSD sliding-window length and how often OSD is evaluated.
OSD_WINDOW_MS = 1000
OSD_CHECK_INTERVAL_MS = 60
OSD_WINDOW_FRAMES = OSD_WINDOW_MS // FRAME_DURATION_MS
OSD_CHECK_INTERVAL_FRAMES = OSD_CHECK_INTERVAL_MS // FRAME_DURATION_MS
# Minimum audio needed before running OSD model.
OSD_MIN_AUDIO_MS = 100
OSD_MIN_AUDIO_SAMPLES = int((OSD_MIN_AUDIO_MS / 1000.0) * SAMPLE_RATE)
# Minimum summed overlap duration in OSD output to count as true overlap.
OSD_MIN_OVERLAP_TOTAL_S = float(os.environ.get("OSD_MIN_OVERLAP_TOTAL_S", "0.18"))
# Initial grace period after TTS starts before OSD can trigger barge-in.
OSD_CHECK_AFTER_ROBOT_START_S = float(os.environ.get("OSD_CHECK_AFTER_ROBOT_START_S", "0.15"))
# Temporal smoothing window for OSD boolean hits.
OSD_HIT_WINDOW_SIZE = int(os.environ.get("OSD_HIT_WINDOW_SIZE", "3"))
# Number of OSD hits required within the smoothing window.
OSD_HITS_REQUIRED_IN_WINDOW = int(os.environ.get("OSD_HITS_REQUIRED_IN_WINDOW", "2"))
# Residual amplification after template subtraction (if template is available).
OSD_RESIDUAL_BOOST = 4.5
# Max gain normalization cap before OSD inference.
OSD_MAX_GAIN = 60.0
# Lag search step size for template alignment (milliseconds).
OSD_TEMPLATE_LAG_STEP_MS = 20
# Whether to apply denoising before OSD inference.
OSD_USE_DENOISE = _env_flag("OSD_USE_DENOISE", default=False)

# Fast overlap heuristic window and cadence (lighter than OSD model).
OVERLAP_CHECK_WINDOW_MS = 600
OVERLAP_CHECK_INTERVAL_MS = 60
OVERLAP_CHECK_WINDOW_FRAMES = OVERLAP_CHECK_WINDOW_MS // FRAME_DURATION_MS
OVERLAP_CHECK_INTERVAL_FRAMES = OVERLAP_CHECK_INTERVAL_MS // FRAME_DURATION_MS
# Absolute residual-ratio threshold for fast overlap trigger.
OVERLAP_MIN_ABS_RESIDUAL_RATIO = float(os.environ.get("OVERLAP_MIN_ABS_RESIDUAL_RATIO", "0.08"))
# Max +/- lag search range for template alignment (milliseconds).
OVERLAP_LAG_OFFSETS_MS = 350
# Required margin above rolling baseline for fast overlap trigger.
OVERLAP_BASELINE_DELTA = float(os.environ.get("OVERLAP_BASELINE_DELTA", "0.015"))
# Baseline history size required before fast overlap can trigger.
OVERLAP_BASELINE_HISTORY_MIN = 2
# Initial grace period after TTS starts before fast overlap can trigger.
OVERLAP_CHECK_AFTER_ROBOT_START_S = 0.1
