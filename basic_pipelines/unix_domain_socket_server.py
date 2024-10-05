import os
import socket
import json
import threading
import logging
from datetime import datetime
from deepdiff import DeepDiff  # You need to install this package

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.last_state = {}  # Initialize last_state to keep track of previous data

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

    def send_event(self, new_data):
        """
        Sends only the differences (diffs) between the new_data and the last sent state.
        """
        # Compute the difference between new_data and last_state
        diff = DeepDiff(self.last_state, new_data, ignore_order=True).to_dict()

        if not diff:
            logger.info("No changes detected. No event sent.")
            return  # No changes to send

        message = json.dumps(diff, default=make_serializable) + "\n"

        with self.lock:
            for client in self.clients[:]:
                try:
                    client.sendall(message.encode('utf-8'))
                    logger.info(f"Sent diff to client: {diff}")
                except BrokenPipeError:
                    logger.warning("Client disconnected.")
                    self.clients.remove(client)
                except Exception as e:
                    logger.error(f"Error sending data to client: {e}")
                    self.clients.remove(client)

        # Update the last_state to the new_data after sending diffs
        self.last_state = new_data.copy()

    def shutdown(self):
        logger.info("Shutting down Unix Domain Socket Server")
        self.running = False
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except Exception as e:
                    logger.error(f"Error closing client socket: {e}")
            self.clients.clear()
def make_serializable(obj):
    if isinstance(obj, set):
        return list(obj)
    # Add other custom serialization logic as needed
    return str(obj)  # Fallback to string representation

# -----------------------------------------------------------------------------------------------
# Example Usage
# -----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    import time

    # Path for the Unix Domain Socket
    SOCKET_PATH = "/tmp/unix_domain_socket_example.sock"

    # Initialize and start the server
    server = UnixDomainSocketServer(SOCKET_PATH)
    server.start()

    try:
        # Simulate data updates
        current_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "value": 100
        }

        while True:
            # Simulate a change in data
            new_value = current_data["value"] + 1
            new_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "value": new_value
            }

            # Send only the diffs
            server.send_event(new_data)

            # Wait for a while before next update
            time.sleep(5)

            current_data = new_data

    except KeyboardInterrupt:
        logger.info("Interrupt received, shutting down...")
    finally:
        server.shutdown()
        server.join()
        # Clean up the socket file
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass
