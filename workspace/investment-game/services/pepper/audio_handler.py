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
REMOTE_REC_IP = "192.168.0.103"
REMOTE_REC_PORT = 9700
FILE_IN_HOST = ""
FILE_IN_PORT = 6000

class PepperAudioDuplex(ALModule):
    def __init__(self, name, remote_ip, remote_port):
        ALModule.__init__(self, name)
        self.remote_addr = (remote_ip, remote_port)
        self.sock = None
        self.is_connected = False
        self.is_muted = False  # The "Software Gate"
        
        self.audio_device = ALProxy("ALAudioDevice")
        self.audio_player = ALProxy("ALAudioPlayer")
        
        # Lower volume reduces structural vibration/clipping
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
        # Using Mode 0 (Master Mix) but we will silence it manually
        self.audio_device.setClientPreferences(self.getName(), 16000, 0, 0)
        self.audio_device.subscribe(self.getName())

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        if self.is_connected:
            try:
                if self.is_muted:
                    # Send a buffer of zeros of the same length to keep the stream alive
                    # but prevent Whisper from hearing anything.
                    silence = '\x00' * len(inputBuffer)
                    self.sock.sendall(silence)
                else:
                    self.sock.sendall(inputBuffer)
            except socket.error:
                self.is_connected = False
        else:
            self.attempt_connect()

    def play_file_gated(self, path):
        """Plays file and manages the mic gate."""
        try:
            print ">> Muting Mic & Playing..."
            self.is_muted = True
            
            # playFile is blocking; the mic stays muted until audio finishes
            self.audio_player.playFile(path)
            
            # Small 'cooldown' to allow for room echo to dissipate
            time.sleep(0.3) 
            self.is_muted = False
            print ">> Unmuting Mic."
        except Exception as e:
            print ">> Playback Error: %s" % e
            self.is_muted = False

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

    print ">> Gated Duplex Ready."

    try:
        while True:
            server.settimeout(1.0)
            try:
                conn, addr = server.accept()
                fd, temp_path = tempfile.mkstemp(suffix=".wav", dir="/tmp/")
                try:
                    with os.fdopen(fd, 'wb') as tmp:
                        while True:
                            data = conn.recv(4096)
                            if not data: break
                            tmp.write(data)
                    
                    # This call is now "Gated"
                    Bridge.play_file_gated(temp_path)
                    
                finally:
                    conn.close()
                    if os.path.exists(temp_path): os.remove(temp_path)
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        Bridge.stop()
        myBroker.shutdown()
        sys.exit(0)