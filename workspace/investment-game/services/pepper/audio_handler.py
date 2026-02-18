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

EYE_ANIM_INTERVAL = 0.1


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
        self.leds = ALProxy("ALLeds")

        self.audio_device.setOutputVolume(70)
        self.attempt_connect()

        # Eye Animation Thread
        self.eye_anim_running = True
        self.local_rms = 0  # Used only for visuals
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
            # We calculate RMS purely for the eye LEDs, not for gating audio.
            # This ensures the robot looks "alive" without affecting the stream.
            audio_data = np.frombuffer(inputBuffer, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            with self.state_lock:
                self.local_rms = rms
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
            self.playback_id += 1
            current_task_id = self.playback_id

        # Stop current speech if any
        try:
            self.audio_player.stopAll()
        except:
            pass

        thread = threading.Thread(
            target=self._playback_worker, args=(path, current_task_id)
        )
        thread.daemon = True
        thread.start()

    def _eye_animation_loop(self):
        """
        Visual feedback only.
        Pulses blue when hearing loud sounds, otherwise white.
        """
        eye_group = "FaceLeds"
        while self.eye_anim_running:
            with self.state_lock:
                current_rms = getattr(self, "local_rms", 0)
                is_speaking = getattr(self, "is_muted", False)

            # Visual threshold for "hearing something"
            if current_rms > 500 and not is_speaking:
                # Listening color (Blue-ish)
                self.leds.post.fadeRGB(eye_group, 0.0, 0.0, 1.0, 0.1)
            else:
                # Idle color (White)
                self.leds.post.fadeRGB(eye_group, 1.0, 1.0, 1.0, 0.2)

            time.sleep(EYE_ANIM_INTERVAL)

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
