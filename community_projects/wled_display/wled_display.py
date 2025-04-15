import socket
import time
import cv2
import numpy as np
from multiprocessing import Process, Queue

class WLEDDisplay:
    """
    A class to control WLED-based LED matrix displays via UDP protocol.

    This class provides functionality to:
    - Control single or multiple LED matrix panels
    - Send frame data via UDP to WLED devices
    - Display debug visualization
    - Handle frame processing in a separate process
    """

    def __init__(
        self,
        # ip="wled-hailo.local", # You can use mDNS if available
        # ip="4.3.2.1", # Or use the IP address directly
        ip="192.168.68.75", # Or use the IP address directly
        port=21324,
        panel_width=None,
        panel_height=None,
        panels=1,
        wled_enabled=True,
    ):
        """
        Initialize the WLED display controller.

        Args:
            ip (str): IP address or hostname of the WLED device
            port (int): UDP port number (default: 21324)
            panel_width (int, optional): Width of each panel in pixels. Defaults to 20 if wled_enabled
            panel_height (int, optional): Height of each panel in pixels. Defaults to 20 if wled_enabled
            panels (int): Number of LED panels to control (default: 1)
            wled_enabled (bool): Enable/disable WLED output (default: True)
        """
        self.ip = ip
        self.port = port
        self.PROTOCOL = 4
        self.TIMEOUT = 1
        self.wled_enabled = wled_enabled

        # Set default panel dimensions based on wled_enabled if not specified
        self.panel_width = panel_width if panel_width is not None else (20 if wled_enabled else 640)
        self.panel_height = panel_height if panel_height is not None else (20 if wled_enabled else 360)

        self.panels = panels
        self.num_leds_per_panel = self.panel_width * self.panel_height
        self.num_leds = self.num_leds_per_panel * panels

        # Calculate the total display dimensions
        self.width = self.panel_width * panels
        self.height = self.panel_height

        # Initialize frame queue
        self.frame_queue = Queue()

        # Initialize UDP socket with mDNS support
        if self.wled_enabled:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.settimeout(2)
                self.sock.sendto(b'', (self.ip, self.port))  # Test connection
            except (socket.gaierror, socket.timeout):
                print(f"Unable to reach {self.ip}. Disabling UDP.")
                self.sock = None
        else:
            self.sock = None

        # Start the process
        self.process = Process(target=self.run)
        self.process.start()

    def create_debug_pattern(self, frame_number):
        """
        Generate a debug pattern for testing LED panel configuration.

        Creates a checkerboard pattern with different colors for each panel,
        alternating based on the frame number.

        Args:
            frame_number (int): Current frame number for pattern animation

        Returns:
            numpy.ndarray: RGB image array of shape (height, width, 3)
        """
        pattern = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for panel in range(self.panels):
            for y in range(self.height):
                for x in range(self.panel_width):
                    if (x + y + frame_number) % 2 == 0:
                        color = (
                            (255, 0, 0) if panel == 0 else (0, 255, 0) if panel == 1 else (0, 0, 255)
                        )
                    else:
                        color = (0, 0, 0)
                    pattern[y, x + panel * self.panel_width] = color
        return pattern

    def image_to_led_data(self, image):
        """
        Convert an image array to LED data format.

        Transforms a numpy image array into a list of RGB tuples suitable
        for LED control.

        Args:
            image (numpy.ndarray): Input image of shape (height, width, 3)

        Returns:
            list: List of RGB tuples [(r,g,b), ...] for each LED
        """
        led_data = []
        for y in range(self.height):
            for x in range(self.width):
                color = image[y, x]
                led_data.append((color[0], color[1], color[2]))
        return led_data

    def convert_to_dnrgb_chunks(self, colors, chunk_size=489):
        """
        Convert RGB colors to WLED UDP protocol chunks.

        Splits the LED data into manageable chunks and formats them according
        to the WLED UDP protocol specification.

        Args:
            colors (list): List of RGB tuples [(r,g,b), ...]
            chunk_size (int): Maximum number of LEDs per chunk (default: 489)

        Returns:
            list: List of bytearray chunks formatted for WLED UDP protocol
        """
        chunks = []
        for panel in range(self.panels):
            start_led = panel * self.num_leds_per_panel
            end_led = start_led + self.num_leds_per_panel
            panel_colors = colors[start_led:end_led]
            for start in range(0, self.num_leds_per_panel, chunk_size):
                chunk = panel_colors[start:start + chunk_size]
                data = bytearray([self.PROTOCOL, self.TIMEOUT])
                data.append(((start + start_led) >> 8) & 0xFF)
                data.append((start + start_led) & 0xFF)
                for color in chunk:
                    data += bytearray([color[2], color[1], color[0]]) # Convert to RGB
                chunks.append(data)
        return chunks

    def run(self):
        """
        Main display loop running in a separate process.

        Continuously monitors the frame queue and sends new frames to the
        LED display when available. This method is automatically started
        by the process created in __init__.
        """
        while True:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                self.send_frame(frame)

    def send_frame(self, frame):
        """
        Send a frame to the LED display.

        Processes and sends the frame data to the WLED device via UDP and
        optionally displays it in a debug window.

        Args:
            frame (numpy.ndarray): RGB image array of shape (height, width, 3)
        """
        # Send LED data via UDP if enabled
        if self.wled_enabled and self.sock:
            # Convert to LED data
            led_data = self.image_to_led_data(frame)
            data_chunks = self.convert_to_dnrgb_chunks(led_data)
            for chunk in data_chunks:
                self.sock.sendto(chunk, (self.ip, self.port))

        # Always display the frame
        duplicate_pixels = 10 if self.wled_enabled else 1 # Duplicate pixels for better visibility
        debug_display = cv2.resize(frame,
                                   (self.width * duplicate_pixels, self.height * duplicate_pixels),
                                   interpolation=cv2.INTER_NEAREST)
        cv2.imshow("Debug Display", debug_display)
        cv2.waitKey(1)  # Prevent window from freezing

    def terminate(self):
        """
        Terminate the display process.

        Cleanly stops the display process and releases associated resources.
        Should be called when the display is no longer needed.
        """
        self.process.terminate()
        self.process.join()

    def __del__(self):
        """
        Cleanup method called when the object is being destroyed.

        Ensures proper cleanup of resources by closing the UDP socket and
        terminating the display process if still running.
        """
        if hasattr(self, 'sock') and self.sock:
            self.sock.close()
        if hasattr(self, 'process') and self.process.is_alive():
            self.terminate()

if __name__ == "__main__":
    """
    Example usage of the WLEDDisplay class.

    Creates a simple animation using the debug pattern generator
    running at 30 FPS.
    """
    wled = WLEDDisplay(panels=1, wled_enabled=True)

    frame_number = 0
    try:
        while True:
            # Generate debug pattern
            debug_frame = wled.create_debug_pattern(frame_number)

            # Enqueue the frame for the display process
            wled.frame_queue.put(debug_frame)

            frame_number += 1
            time.sleep(1 / 30)  # 30 FPS
    except KeyboardInterrupt:
        print("Animation stopped.")
    finally:
        wled.terminate()
        cv2.destroyAllWindows()
