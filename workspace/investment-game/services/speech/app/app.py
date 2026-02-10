import threading
import sys

from socket_server import start_sock_server
from http_server import start_fastapi

sys.stdout.reconfigure(line_buffering=True)


def main():
    threading.Thread(target=start_fastapi, daemon=True).start()
    start_sock_server()


if __name__ == "__main__":
    main()
