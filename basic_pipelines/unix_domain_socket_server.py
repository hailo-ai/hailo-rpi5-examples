import os
import socket
import json
import threading
import logging
from datetime import datetime
from deepdiff import DeepDiff
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------------------------
# Unix Domain Socket Server
# -----------------------------------------------------------------------------------------------
class UnixDomainSocketServer(threading.Thread):
    UPTIME_WINDOW_SIZE = 100  # Number of events to track per object
    APPEAR_THRESHOLD = 0.6
    DISAPPEAR_THRESHOLD = 0.3

    def __init__(self, socket_path):
        super().__init__()
        self.socket_path = socket_path
        self.clients = []
        self.lock = threading.Lock()
        self.running = True
        self.last_state = {}
        self.object_logs = {}  # To track detections per object

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
        Implements object uptime for visibility detection.
        """
        # Compute the difference between new_data and last_state
        diff = DeepDiff(self.last_state, new_data, ignore_order=True).to_dict()

        if not diff:
            logger.info("No changes detected. No event sent.")
            return  # No changes to send

        # Update object logs
        detected_objects = set(obj['id'] for obj in new_data.get('objects', []))
        for obj_id in detected_objects:
            if obj_id not in self.object_logs:
                self.object_logs[obj_id] = deque(maxlen=self.UPTIME_WINDOW_SIZE)
            self.object_logs[obj_id].append(1)  # Detected

        # Update logs for objects not detected in this event
        for obj_id in list(self.object_logs.keys()):
            if obj_id not in detected_objects:
                self.object_logs[obj_id].append(0)  # Not detected

        # Determine currently viewable objects based on uptime
        visible_objects = []
        for obj_id, log in self.object_logs.items():
            uptime = sum(log) / len(log)
            if uptime >= self.APPEAR_THRESHOLD:
                visible_objects.append(obj_id)
            elif uptime < self.DISAPPEAR_THRESHOLD and obj_id in self.last_state.get('objects', [{}]):
                # Fire disappearance event
                disappearance_event = {'event': 'object_disappeared', 'object_id': obj_id}
                self._send_message(disappearance_event)
                del self.object_logs[obj_id]  # Remove object from logs

        # Initialize last_sent_visible_objects if not already done
        if not hasattr(self, 'last_sent_visible_objects'):
            self.last_sent_visible_objects = set()

        # Convert lists to sets for comparison
        current_visible = set(visible_objects)
        last_visible = self.last_sent_visible_objects

        # Check if there is a change in visible objects
        if current_visible != last_visible:
            message = json.dumps({'visible_objects': list(current_visible)}, default=make_serializable) + "\n"
            
            with self.lock:
                for client in self.clients[:]:
                    try:
                        client.sendall(message.encode('utf-8'))
                        logger.info(f"Sent visible objects to client: {current_visible}")
                    except BrokenPipeError:
                        logger.warning("Client disconnected.")
                        self.clients.remove(client)
                    except Exception as e:
                        logger.error(f"Error sending data to client: {e}")
                        self.clients.remove(client)
            
            # Update the last sent visible objects
            self.last_sent_visible_objects = current_visible.copy()

        # Update the last_state to the new_data after sending diffs
        self.last_state = new_data.copy()
    
    def _send_message(self, message):
        message_str = json.dumps(message) + "\n"
        with self.lock:
            for client in self.clients[:]:
                try:
                    client.sendall(message_str.encode('utf-8'))
                    logger.info(f"Sent event to client: {message}")
                except BrokenPipeError:
                    logger.warning("Client disconnected.")
                    self.clients.remove(client)
                except Exception as e:
                    logger.error(f"Error sending event to client: {e}")
                    self.clients.remove(client)

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
            "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
            "value": 100,
            "objects": [{"id": "object1"}, {"id": "object2"}]
        }

        while True:
            # Simulate a change in data
            new_value = current_data["value"] + 1
            # Example: object2 becomes object3
            new_data = {
                "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
                "value": new_value,
                "objects": [{"id": "object1"}, {"id": "object3"}]
            }

            # Send only the diffs with uptime processing
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