import socket
import time
import sys
import os
import tempfile
import threading
import numpy as np
from naoqi import ALProxy, ALModule, ALBroker

PEPPER_IP = "127.0.0.1"
NAOQI_PORT = 9559
REMOTE_REC_IP = os.environ.get("REMOTE_REC_IP", "192.168.0.102")
REMOTE_REC_PORT = 9700

FILE_IN_HOST = ""
FILE_IN_PORT = 6000

EYE_GROUP = "FaceLeds"
PULSE_DURATION = 0.5


# Generated with Gemini 3 Pro with minor tweaks
class PepperAudioDuplex(ALModule):
    def __init__(self, name, remote_ip, remote_port):
        ALModule.__init__(self, name)
        self.remote_addr = (remote_ip, remote_port)
        self.sock = None
        self.is_connected = False

        # Robot state
        self.is_muted = False
        self.playback_id = 0
        self.state_lock = threading.Lock()

        # Proxies
        self.audio_device = ALProxy("ALAudioDevice")
        self.audio_player = ALProxy("ALAudioPlayer")
        self.memory = ALProxy("ALMemory")
        self.leds = ALProxy("ALLeds")

        # Audio
        self.audio_device.setOutputVolume(50)
        self.attempt_connect()

        # Eye Animation
        self.memory.subscribeToEvent("GlobalEyeState", self.getName(), "on_eye_state")
        self.eye_anim_running = True
        thread = threading.Thread(target=self._eye_animation_loop)
        thread.setDaemon(True)
        thread.start()

    def attempt_connect(self):
        try:
            if self.sock:
                self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1.0)
            self.sock.connect(self.remote_addr)
            self.is_connected = True

            print("Connected to Audio Receiver.")
        except:
            self.is_connected = False

    def start_streaming(self):
        # 16000Hz
        # Channel Map 3 = Front Microphone (Directional, better quality)
        # Deinterleaving 0 = Disabled (Mono output is fine)
        self.audio_device.setClientPreferences(self.getName(), 16000, 3, 0)
        self.audio_device.subscribe(self.getName())
        print("Subscribed to Front Mic @ 16kHz")

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        if not self.is_connected:
            self.attempt_connect()
            return

        try:
            with self.state_lock:
                i_am_speaking = self.is_muted

            if i_am_speaking:
                silence = b"\x00" * len(inputBuffer)
                self.sock.sendall(silence)
            else:
                self.sock.sendall(inputBuffer)

        except socket.error:
            self.is_connected = False
            print("Socket error, disconnecting.")
        except Exception as exception:
            print("Error in processRemote:", exception)

    def _playback_worker(self, path, task_id):
        try:
            with self.state_lock:
                self.is_muted = True

            self.audio_player.playFile(path)
            # Small buffer to ensure audio fully clears room reverb
            time.sleep(0.2)
        except Exception as exception:
            print("Playback interrupted:", exception)
        finally:
            with self.state_lock:
                if self.playback_id == task_id:
                    self.is_muted = False
                    print("Audio finished. Mic unmuted.")

    def play_file_gated(self, path):
        with self.state_lock:
            if self.is_muted:
                print(
                    "Robot is already speaking. Dropping received file: {}".format(path)
                )

                try:
                    os.remove(path)
                except:
                    pass
                return

            self.playback_id += 1
            current_task_id = self.playback_id

        thread = threading.Thread(
            target=self._playback_worker, args=(path, current_task_id)
        )
        thread.daemon = True
        thread.start()

    def on_eye_state(self, key, value, message):
        print("Eye state event:" + value)
        self.current_eye_state = value

    def _eye_animation_loop(self):
        while self.eye_anim_running:
            with self.state_lock:
                is_speaking = getattr(self, "is_muted", False)
                global_state = getattr(self, "current_eye_state", "idle")

            if is_speaking:
                effective_state = "speaking"
            elif global_state in ["listening", "processing"]:
                effective_state = global_state
            else:
                effective_state = "idle"

            if effective_state == "speaking":
                if self.pulse_state == 0:
                    self.leds.post.fadeRGB(EYE_GROUP, 0.0, 1.0, 0.0, PULSE_DURATION)
                    self.pulse_state = 1
                else:
                    self.leds.post.fadeRGB(EYE_GROUP, 0.0, 0.2, 0.0, PULSE_DURATION)
                    self.pulse_state = 0

                time.sleep(PULSE_DURATION)

            elif effective_state == "listening":
                if self.pulse_state == 0:
                    self.leds.post.fadeRGB(EYE_GROUP, 0.0, 0.0, 1.0, PULSE_DURATION)
                    self.pulse_state = 1
                else:
                    self.leds.post.fadeRGB(EYE_GROUP, 0.0, 0.0, 0.2, PULSE_DURATION)
                    self.pulse_state = 0

                time.sleep(PULSE_DURATION)

            elif effective_state == "processing":
                if self.pulse_state == 0:
                    self.leds.post.fadeRGB(EYE_GROUP, 1.0, 0.5, 0.0, PULSE_DURATION)
                    self.pulse_state = 1
                else:
                    self.leds.post.fadeRGB(EYE_GROUP, 0.2, 0.1, 0.0, PULSE_DURATION)
                    self.pulse_state = 0

                time.sleep(PULSE_DURATION)

            else:
                self.leds.post.fadeRGB(EYE_GROUP, 1.0, 1.0, 1.0, 0.2)
                self.pulse_state = 0

                time.sleep(0.5)

    def stop(self):
        try:
            self.audio_device.unsubscribe(self.getName())
            self.eye_anim_running = False
            if self.sock:
                self.sock.close()
        except:
            pass


if __name__ == "__main__":
    myBroker = ALBroker("myBroker", "0.0.0.0", 0, PEPPER_IP, NAOQI_PORT)
    Bridge = PepperAudioDuplex("Bridge", REMOTE_REC_IP, REMOTE_REC_PORT)
    Bridge.start_streaming()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((FILE_IN_HOST, FILE_IN_PORT))
    server.listen(1)

    print("Gated Duplex Ready (Front Mic)")

    try:
        while True:
            server.settimeout(0.5)
            try:
                conn, addr = server.accept()
                fd, temp_path = tempfile.mkstemp(suffix=".wav", dir="/tmp/")
                try:
                    with os.fdopen(fd, "wb") as tmp:
                        while True:
                            data = conn.recv(4096)
                            if not data:
                                break
                            tmp.write(data)
                    Bridge.play_file_gated(temp_path)
                finally:
                    conn.close()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        Bridge.stop()
        myBroker.shutdown()
        sys.exit(0)
