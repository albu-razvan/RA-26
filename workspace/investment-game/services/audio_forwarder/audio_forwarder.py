import subprocess
import time

TARGET_IP = "192.168.0.102"
TARGET_PORT = "9700"


def main():
    print("Attempting to connect to {}:{}...".format(TARGET_IP, TARGET_PORT))

    arecord = subprocess.Popen(
        [
            "arecord",
            "-D",
            "default",
            "-f",
            "S16_LE",
            "-r",
            "16000",
            "-c",
            "1",
            "-t",
            "raw",
        ],
        stdout=subprocess.PIPE,
    )

    netcat = subprocess.Popen(["nc", TARGET_IP, TARGET_PORT], stdin=arecord.stdout)
    arecord.stdout.close()

    try:
        netcat.wait()
        print("Connection closed. Restarting in 3 seconds...")
    except KeyboardInterrupt:
        arecord.terminate()
        netcat.terminate()

        return

    try:
        arecord.terminate()
        netcat.terminate()
    except:
        pass

    time.sleep(3)
    return main()


if __name__ == "__main__":
    main()
