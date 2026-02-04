import socket

PEPPER_IP = "192.168.0.100"
PEPPER_PORT = 6000


def send_tts_to_pepper(sound_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((PEPPER_IP, PEPPER_PORT))

    file = open(sound_file, "rb")
    try:
        data = file.read(4096)
        while data:
            sock.send(data)
            data = file.read(4096)
    finally:
        file.close()

    sock.close()

    print("Sent TTS to Pepper: '{}'".format(sound_file))
