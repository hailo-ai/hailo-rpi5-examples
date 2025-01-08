import socket
import time
import cv2
import numpy as np
from multiprocessing import Process, Queue

class WLEDDisplay:
    PROTOCOL = 4
    TIMEOUT = 1

    def __init__(
        self,
        # ip="wled-hailo.local", # You can use mDNS if available
        ip="4.3.2.1", # Or use the IP address directly
        port=21324,
        panel_width=20,
        panel_height=20,
        panels=1,
        udp_enabled=True,
    ):
        self.ip = ip
        self.port = port
        self.panel_width = panel_width
        self.panel_height = panel_height
        self.panels = panels
        self.udp_enabled = udp_enabled
        self.num_leds_per_panel = panel_width * panel_height
        self.num_leds = self.num_leds_per_panel * panels
        self.frame_queue = Queue()

        # Initialize UDP socket with mDNS support
        if self.udp_enabled:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.settimeout(2)
                self.sock.sendto(b'', (self.ip, self.port))  # Test connection
            except (socket.gaierror, socket.timeout):
                print(f"Unable to reach {self.ip}. Disabling UDP.")
                self.sock = None
                self.udp_enabled = False
        else:
            self.sock = None

        # Start the process
        self.process = Process(target=self.run)
        self.process.start()

    def apply_filters(self, image, saturation=1.0, brightness=1.0, vibrant=False):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        s = cv2.multiply(s, saturation)
        v = cv2.multiply(v, brightness)
        if vibrant:
            v = cv2.addWeighted(v, 1.5, v, 0, -50)
        s = np.clip(s, 0, 255).astype(np.uint8)
        v = np.clip(v, 0, 255).astype(np.uint8)
        hsv_filtered = cv2.merge([h, s, v])
        return cv2.cvtColor(hsv_filtered, cv2.COLOR_HSV2BGR)

    def create_debug_pattern(self, frame_number):
        pattern = np.zeros((self.panel_height, self.panel_width * self.panels, 3), dtype=np.uint8)
        for panel in range(self.panels):
            for y in range(self.panel_height):
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
        led_data = []
        for y in range(self.panel_height):
            for x in range(self.panel_width * self.panels):
                color = image[y, x]
                led_data.append((color[0], color[1], color[2]))
        return led_data

    def convert_to_dnrgb_chunks(self, colors, chunk_size=489):
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
        """Run the display loop in a separate process."""
        while True:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                self.send_frame(frame)

    def send_frame(self, frame):
        # Convert to LED data
        led_data = self.image_to_led_data(frame)

        # Send LED data via UDP if enabled
        if self.udp_enabled and self.sock:
            data_chunks = self.convert_to_dnrgb_chunks(led_data)
            for chunk in data_chunks:
                self.sock.sendto(chunk, (self.ip, self.port))

        # Always display the frame
        debug_display = cv2.resize(frame, (400 * self.panels, 400), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("Debug Display", debug_display)
        cv2.waitKey(1)  # Prevent window from freezing

    def terminate(self):
        """Terminate the display process."""
        self.process.terminate()
        self.process.join()

if __name__ == "__main__":
    wled = WLEDDisplay(panels=2, udp_enabled=True)

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