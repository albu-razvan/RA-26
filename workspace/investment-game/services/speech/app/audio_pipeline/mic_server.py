import socket

from audio_pipeline.constants import HOST, PORT_MIC


class MicServer:
    def __init__(self, audio_processor):
        self.processor = audio_processor

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, PORT_MIC))
        sock.listen(1)
        print("[MIC] Listening on {}:{}".format(HOST, PORT_MIC))

        while True:
            conn, addr = sock.accept()
            print("[MIC] Connected from {}".format(addr))
            self._handle(conn)

    def _handle(self, conn):
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break

                self.processor.process_stream(data)
        except Exception as exception:
            print("[MIC] Connection error: {}".format(exception))
        finally:
            conn.close()
            print("[MIC] Connection closed")
            self.processor.reset_after_disconnect()
