is_user_talking = False
current_version = 0
robot_speak_end_time = 0.0

# Robot TTS template for fast overlap detection (mic contains both robot and user)
robot_tts_start_time = 0.0
robot_tts_pcm_16k = None  # numpy array (int16)
