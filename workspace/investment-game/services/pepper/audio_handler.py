#!/usr/bin/env python
# -*- encoding: UTF-8 -*-

import socket
import time
import sys
import os
import tempfile
import threading
from naoqi import ALProxy, ALModule, ALBroker

# --- CONFIGURATION ---
PEPPER_IP = "127.0.0.1"
NAOQI_PORT = 9559
REMOTE_REC_IP = "192.168.0.102"
REMOTE_REC_PORT = 9700
FILE_IN_HOST = ""
FILE_IN_PORT = 6000

class PepperAudioDuplex(ALModule):
    def __init__(self, name, remote_ip, remote_port):
        ALModule.__init__(self, name)
        self.remote_addr = (remote_ip, remote_port)
        self.sock = None
        self.is_connected = False
        
        # --- STATE MANAGEMENT ---
        self.is_muted = False
        self.playback_id = 0  # To track which audio task is currently "owner" of the gate
        self.state_lock = threading.Lock()
        
        self.audio_device = ALProxy("ALAudioDevice")
        self.audio_player = ALProxy("ALAudioPlayer")
        
        self.audio_device.setOutputVolume(50)
        self.attempt_connect()

    def attempt_connect(self):
        try:
            if self.sock: self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1.0) 
            self.sock.connect(self.remote_addr)
            self.is_connected = True
            print ">> Connected to Whisper Receiver."
        except:
            self.is_connected = False

    def start_streaming(self):
        self.audio_device.setClientPreferences(self.getName(), 16000, 0, 0)
        self.audio_device.subscribe(self.getName())

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        """
        Callback from ALAudioDevice. 
        If is_muted is True, we send empty bytes to keep the pipe open
        but prevent the remote Whisper AI from hearing the robot's own voice.
        """
        if self.is_connected:
            try:
                if self.is_muted:
                    silence = '\x00' * len(inputBuffer)
                    self.sock.sendall(silence)
                else:
                    self.sock.sendall(inputBuffer)
            except socket.error:
                self.is_connected = False
        else:
            self.attempt_connect()

    def _playback_worker(self, path, my_task_id):
        """
        Runs in a background thread.
        Plays audio and manages the gate ONLY if it is still the active task.
        """
        try:
            # 1. Engage Gate
            self.is_muted = True
            
            # 2. Play Audio (This blocks THIS thread, but not the main loop)
            # using stopAll() in the main thread will cause this to return/throw
            self.audio_player.playFile(path)
            
            # Optional: Small cooldown for room echo
            time.sleep(0.3)
            
        except Exception as e:
            print ">> Playback interrupted or failed: %s" % e
        finally:
            # 3. Safe Disengage
            # We only unmute if WE are still the current task. 
            # If a new file came in, playback_id has incremented, so we do NOT unmute.
            with self.state_lock:
                if self.playback_id == my_task_id:
                    self.is_muted = False
                    print ">> Audio finished. Mic Unmuted."
                else:
                    print ">> Audio Interrupted. Keeping Mic Muted for next file."

    def play_file_gated(self, path):
        """
        Non-blocking entry point. 
        Stops previous audio immediately and starts new audio.
        """
        with self.state_lock:
            # Increment ID so any running thread knows it's now "obsolete"
            self.playback_id += 1
            current_task_id = self.playback_id
        
        print ">> Received Audio. Interrupting previous and playing..."
        
        # Stop any current playback immediately
        try:
            self.audio_player.stopAll()
        except:
            pass

        # Start new playback in background thread
        t = threading.Thread(target=self._playback_worker, args=(path, current_task_id))
        t.start()

    def stop(self):
        try:
            self.audio_device.unsubscribe(self.getName())
            if self.sock: self.sock.close()
        except: pass

if __name__ == "__main__":
    myBroker = ALBroker("myBroker", "0.0.0.0", 0, PEPPER_IP, NAOQI_PORT)
    Bridge = PepperAudioDuplex("Bridge", REMOTE_REC_IP, REMOTE_REC_PORT)
    Bridge.start_streaming()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((FILE_IN_HOST, FILE_IN_PORT))
    server.listen(1)

    print ">> Gated Duplex Ready (Async Mode)."

    try:
        while True:
            # Checks for new connections every 0.1s so it's responsive
            server.settimeout(0.1)
            try:
                conn, addr = server.accept()
                fd, temp_path = tempfile.mkstemp(suffix=".wav", dir="/tmp/")
                try:
                    # Read the file
                    with os.fdopen(fd, 'wb') as tmp:
                        while True:
                            data = conn.recv(4096)
                            if not data: break
                            tmp.write(data)
                    
                    # This is now NON-BLOCKING.
                    # It will instantly return to the top of the loop 
                    # ready to accept a NEW file to interrupt this one.
                    Bridge.play_file_gated(temp_path)
                    
                finally:
                    conn.close()
                    # We do NOT remove the file immediately here because 
                    # the background thread needs it. 
                    # You might need a separate cleaner or accept /tmp growth (it clears on reboot).
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        Bridge.stop()
        myBroker.shutdown()
        sys.exit(0)