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
        self.last_sent_visible_objects = set() # To track visible objects


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

    def send_event(self, event_payload):
        """
        Sends only the differences (diffs) between the new_data and the last sent state.
        Implements object uptime for visibility detection.
        """
        new_state = self._event_payload_to_state(event_payload)
        differences = self.compute_differences(new_state)
    
        if not differences:
            logger.info("No changes detected. No event sent.")
            return
    
        self.update_object_logs(new_state)
        currently_visible_objects = self.determine_visible_objects()
    
        self.send_visible_objects(currently_visible_objects)
    
        self.update_last_state(new_state)
    
    def _event_payload_to_state(self, event_payload):
        """
        Converts new_data list to dictionary format with full word keys.
        """
        return {'objects': [{'id': object_id} for object_id in event_payload]}
    
    def compute_differences(self, new_state):
        """
        Computes the difference between the new_data and last_state.
        """
        return DeepDiff(self.last_state, new_state, ignore_order=True) != {}
    
    def update_object_logs(self, new_state):
        """
        Updates object logs based on detected object IDs.
        """
        objects = new_state.get('objects', [])
        detected_object_ids = set(object['id'] for object in objects)
        for object_id in detected_object_ids:
            if object_id not in self.object_logs:
                self.object_logs[object_id] = deque(maxlen=self.UPTIME_WINDOW_SIZE)
            self.object_logs[object_id].append(1)  # Object detected
    
        for object_id in list(self.object_logs.keys()):
            if object_id not in detected_object_ids:
                self.object_logs[object_id].append(0)  # Object not detected

        # Remove objects that are not detected for a long time
        for object_id, log in self.object_logs.items():
            if len(log) == self.UPTIME_WINDOW_SIZE and sum(log) == 0:
                del self.object_logs[object_id]
        
        return detected_object_ids
    
    def determine_visible_objects(self):
        """
        Determines currently viewable objects based on uptime.
        An object becomes visible once uptime_ratio >= APPEAR_THRESHOLD and remains visible until uptime_ratio < DISAPPEAR_THRESHOLD.
        """
        for object_id, log in self.object_logs.items():
            uptime_ratio = sum(log) / len(log)
            if object_id in self.last_sent_visible_objects:
                if uptime_ratio < self.DISAPPEAR_THRESHOLD:
                    disappearance_event = {'event': 'object_disappeared', 'object_id': object_id}
                    self.send_message_to_client(disappearance_event)
                    self.last_sent_visible_objects.remove(object_id)
            else:
                if uptime_ratio >= self.APPEAR_THRESHOLD:
                    appearance_event = {'event': 'object_appeared', 'object_id': object_id}
                    self.send_message_to_client(appearance_event)
                    self.last_sent_visible_objects.add(object_id)
        return list(self.last_sent_visible_objects)    
    
    def _object_existed(self, object_id):
        return object_id in self.last_state.get('objects', [{}])[0]
    
    def has_visible_objects_changed(self, currently_visible_objects):
        """
        Checks if there is a change in visible objects.
        """
        if not hasattr(self, 'last_sent_visible_objects'):
            self.last_sent_visible_objects = set()
        current_visible_set = set(currently_visible_objects)
        last_visible_set = self.last_sent_visible_objects
        if current_visible_set != last_visible_set:
            self.current_visible_set = current_visible_set
            return True
        return False
    
    def send_visible_objects(self, currently_visible_objects):
        """
        Sends the list of currently visible objects to clients.
        """
        message = json.dumps({'visible_objects': list(self.current_visible_set)}, default=make_serializable) + "\n"
        with self.lock:
            for client_connection in self.clients[:]:
                try:
                    client_connection.sendall(message.encode('utf-8'))
                    logger.info(f"Sent visible objects to client: {self.current_visible_set}")
                except BrokenPipeError:
                    logger.warning("Client disconnected.")
                    self.clients.remove(client_connection)
                except Exception as exception_error:
                    logger.error(f"Error sending data to client: {exception_error}")
                    self.clients.remove(client_connection)
        self.last_sent_visible_objects = self.current_visible_set.copy()
    
    def update_last_state(self, new_data_dictionary):
        """
        Updates the last_state to the new_data after sending diffs.
        """
        self.last_state = new_data_dictionary.copy()
    
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