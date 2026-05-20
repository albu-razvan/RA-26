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
REMOTE_REC_PORT = int(os.environ.get("REMOTE_REC_PORT", "9702"))

FILE_IN_HOST = ""
FILE_IN_PORT = 6000

LOCAL_CTRL_PORT = 9703

EYE_GROUP = "FaceLeds"
PULSE_DURATION = 0.5


class PepperAudioDuplex(ALModule):
    def __init__(self, name, remote_ip, remote_port):
        ALModule.__init__(self, name)
        self.remote_addr = (remote_ip, remote_port)
        self.sock = None
        self.is_connected = False

        # Robot state
        self.pepper_is_speaking = False
        self.playback_id = 0
        self.current_playback_file = None
        self.state_lock = threading.Lock()

        # Proxies
        self.audio_device = ALProxy("ALAudioDevice")
        self.audio_player = ALProxy("ALAudioPlayer")
        self.memory = ALProxy("ALMemory")
        self.leds = ALProxy("ALLeds")

        # Audio setup
        self.audio_device.setOutputVolume(70)
        self.attempt_connect()

        try:
            self.memory.subscribeToEvent("ALAudioPlayer/AudioPlaying", self.getName(), "on_audio_playing")
            print("Subscribed to AudioPlaying event")
        except Exception as e:
            print("Could not subscribe to AudioPlaying event:", e)

        # Eye state
        self.memory.subscribeToEvent("GlobalEyeState", self.getName(), "on_eye_state")
        self.current_eye_state = "idle"
        self.pulse_state = 0
        self.eye_anim_running = True

        thread = threading.Thread(target=self._eye_animation_loop)
        thread.daemon = True
        thread.start()

    # -------------------------
    # Audio streaming
    # -------------------------
    def attempt_connect(self):
        try:
            if self.sock:
                self.sock.close()

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1.0)
            self.sock.connect(self.remote_addr)
            self.is_connected = True
            print("Connected to Audio Receiver.")
        except Exception as e:
            print("Audio connect failed:", e)
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
            self.sock.sendall(inputBuffer)
        except socket.error as e:
            print("Socket error:", e)
            self.is_connected = False
        except Exception as e:
            print("processRemote error:", e)

    # -------------------------
    # Playback
    # -------------------------
    def on_audio_playing(self, key, value, message):
        print("Audio playing:", value)
        with self.state_lock:
            self.pepper_is_speaking = bool(value)

    def _playback_worker(self, path, task_id):
        try:
            with self.state_lock:
                self.pepper_is_speaking = True
                self.current_playback_file = path

            # self._send_ctrl(b"P")  # Disabled - using separate ports now
            self.audio_player.playFile(path)
            time.sleep(0.2)

        except Exception as e:
            print("Playback error:", e)

        finally:
            with self.state_lock:
                if self.current_playback_file == path:
                    self.current_playback_file = None
                if self.playback_id == task_id:
                    self.pepper_is_speaking = False
                    print("Audio finished.")

            # self._send_ctrl(b"S")  # Disabled - using separate ports now

    def stop_playback(self):
        with self.state_lock:
            self.pepper_is_speaking = False
            self.current_playback_file = None

        try:
            self.audio_player.stopAll()
            print("Playback stopped")
        except Exception as e:
            print("Stop error:", e)

    def play_file_gated(self, path):
        with self.state_lock:
            if self.pepper_is_speaking:
                print("Dropping file (already speaking):", path)
                try:
                    os.remove(path)
                except Exception:
                    pass
                return

            self.playback_id += 1
            task_id = self.playback_id

        thread = threading.Thread(
            target=self._playback_worker, args=(path, task_id)
        )
        thread.daemon = True
        thread.start()

    # -------------------------
    # Eye animation
    # -------------------------
    def on_eye_state(self, key, value, message):
        print("Eye state:", value)
        self.current_eye_state = value

    def _eye_animation_loop(self):
        while self.eye_anim_running:
            with self.state_lock:
                speaking = self.pepper_is_speaking
                state = getattr(self, "current_eye_state", "idle")

            if speaking or state == "speaking":
                effective = "speaking"
            elif state in ["listening", "processing"]:
                effective = state
            else:
                effective = "idle"

            if effective == "speaking":
                self._pulse(0.0, 1.0, 0.0)
            elif effective == "listening":
                self._pulse(0.0, 0.0, 1.0)
            elif effective == "processing":
                self._pulse(1.0, 0.5, 0.0)
            else:
                self.leds.post.fadeRGB(EYE_GROUP, 1.0, 1.0, 1.0, 0.2)
                self.pulse_state = 0
                time.sleep(0.5)

    def _pulse(self, r, g, b):
        if self.pulse_state == 0:
            self.leds.post.fadeRGB(EYE_GROUP, r, g, b, PULSE_DURATION)
            self.pulse_state = 1
        else:
            self.leds.post.fadeRGB(EYE_GROUP, r * 0.2, g * 0.2, b * 0.2, PULSE_DURATION)
            self.pulse_state = 0
        time.sleep(PULSE_DURATION)

    # -------------------------
    def stop(self):
        try:
            self.audio_device.unsubscribe(self.getName())
            self.eye_anim_running = False
            if self.sock:
                self.sock.close()
        except Exception:
            pass


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    myBroker = ALBroker("myBroker", "0.0.0.0", 0, PEPPER_IP, NAOQI_PORT)

    Bridge = PepperAudioDuplex("Bridge", REMOTE_REC_IP, REMOTE_REC_PORT)
    Bridge.start_streaming()

    # -------------------------
    # Local control server
    # -------------------------
    def start_local_ctrl_server():
        ctrl_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ctrl_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ctrl_server.bind(("127.0.0.1", LOCAL_CTRL_PORT))
        ctrl_server.listen(1)

        print("Local control server on 127.0.0.1:%d" % LOCAL_CTRL_PORT)

        while True:
            try:
                conn, addr = ctrl_server.accept()

                data = ""
                while len(data) < 3:
                    chunk = conn.recv(3 - len(data))
                    if not chunk:
                        break
                    data += chunk

                if data == "\x00\x00S":
                    Bridge.stop_playback()
                    print("Interrupt received")

                conn.close()

            except Exception as e:
                print("Local ctrl error:", e)

    t = threading.Thread(target=start_local_ctrl_server)
    t.daemon = True
    t.start()

    # -------------------------
    # File receiver
    # -------------------------
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((FILE_IN_HOST, FILE_IN_PORT))
    server.listen(1)

    print("Gated Duplex Ready")

    def handle_connection(conn):
        try:
            header = conn.recv(2)
            if not header or len(header) < 2:
                return

            # Control command
            if header == "\x00\x00":
                cmd = conn.recv(1)
                if cmd == "S":
                    Bridge.stop_playback()
                    print("Stop command received")
                return

            fd, path = tempfile.mkstemp(suffix=".wav", dir="/tmp/")

            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(header)

                    while True:
                        data = conn.recv(4096)
                        if not data:
                            break
                        f.write(data)

                Bridge.play_file_gated(path)

            except Exception as e:
                print("File write error:", e)

        finally:
            conn.close()

    try:
        while True:
            server.settimeout(0.5)
            try:
                conn, addr = server.accept()
                handle_connection(conn)
            except socket.timeout:
                continue

    except KeyboardInterrupt:
        Bridge.stop()
        myBroker.shutdown()
        sys.exit(0)
