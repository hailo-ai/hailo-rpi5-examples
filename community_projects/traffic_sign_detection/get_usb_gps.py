import pynmea2
import serial
import time
import os
import io

def get_usb_gps_devices():
    """
    Get a list of GPS devices that are connected via USB.
    """
    for device in [f'/dev/{device}' for device in os.listdir('/dev') if 'USB' in device]:
        try:
            ser = serial.Serial(device, 9600, timeout=1.0)  # parse data, wait & collect new data for 1 second timeout, then parse buffered
            sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
            start_time = time.time()
            while time.time() - start_time < 10000:  # wait up to 10 seconds to get a GPS fix
                try:
                    line = sio.readline()
                    msg = pynmea2.parse(line)
                    if hasattr(msg, 'latitude') or hasattr(msg, 'longitude'):
                        return device
                except Exception as e:
                    continue
        except Exception as e:
            continue
    return None  # no GPS devices found

def main():
    # for the example usage, we will print the USB GPS device if found
    usb_gps_device = get_usb_gps_devices()

    if usb_gps_device:
        print(f"USB GPS found on: {usb_gps_device}")
    else:
        print("No available USB GPS found.")

if __name__ == "__main__":
    # example usage
    main()
