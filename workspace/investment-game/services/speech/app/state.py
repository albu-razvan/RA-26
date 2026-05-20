is_user_talking = False
current_version = 0
robot_is_speaking = False
robot_ignore_vad_until = 0.0
queued_speech_waiters = 0
speech_cancel_generation = 0

# Robot TTS template for fast overlap detection (mic contains both robot and user)
robot_tts_start_time = 0.0
robot_tts_pcm_16k = None  # numpy array (int16)
