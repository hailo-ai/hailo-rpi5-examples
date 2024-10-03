import os
import socket
import json
import threading
import logging

from datetime import datetime


# -----------------------------------------------------------------------------------------------
# Unix Domain Socket Server
# -----------------------------------------------------------------------------------------------
class UnixDomainSocketServer(threading.Thread):
    def __init__(self, socket_path):
        super().__init__()
        self.socket_path = socket_path
        self.clients = []
        self.lock = threading.Lock()
        self.running = True

        # Ensure the socket does not already exist
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass

        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.socket_path)
        self.server.listen(5)
        self.server.settimeout(1.0)  # To allow periodic checking for shutdown
        logger.info(f"Unix Domain Socket Server initialized at {socket_path}")

    def run(self):
        logger.info("Unix Domain Socket Server started")
        while self.running:
            try:
                client, _ = self.server.accept()
                with self.lock:
                    self.clients.append(client)
                logger.info("New client connected.")
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Socket accept error: {e}")
                break

        self.server.close()
        logger.info("Unix Domain Socket Server shut down.")

    def send_event(self, data):
        message = json.dumps(data) + "\n"
        with self.lock:
            for client in self.clients[:]:
                try:
                    client.sendall(message.encode('utf-8'))
                except BrokenPipeError:
                    logger.warning("Client disconnected.")
                    self.clients.remove(client)
                except Exception as e:
                    logger.error(f"Error sending data to client: {e}")
                    self.clients.remove(client)

    def shutdown(self):
        logger.info("Shutting down Unix Domain Socket Server")
        self.running = False
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients.clear()

