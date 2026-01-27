from naoqi import ALProxy
import tempfile
import socket
import os

HOST = ""
PORT = 6000

print("Starting Pepper audio player...")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)

audio_player = ALProxy("ALAudioPlayer", "127.0.0.1", 9559)

while True:
    print("Waiting for incoming audio...")
    conn, addr = server.accept()
    print("Connected by {}".format(addr))

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_file_name = temp_file.name

    while True:
        data = conn.recv(4096)
        if not data:
            break

        temp_file.write(data)

    temp_file.close()
    conn.close()

    print("Audio received: {}".format(temp_file_name))

    audio_player.playFile(temp_file_name)
    print("Audio played on Pepper")

    try:
        os.remove(temp_file_name)
    except Exception as exception:
        print("Could not delete temp file:", exception)
