import pynmea2
import serial
import io

if __name__ == "__main__":
    usb_path = '/dev/ttyUSB0'  # or any other path you want to use
    ser = serial.Serial(usb_path, 9600, timeout=1.0)  # parse data, wait & collect new data for 1 second, then parse buffered
    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
    while True:
        try:
            line = sio.readline()
            msg = pynmea2.parse(line)
            print(msg)
            if hasattr(msg, 'latitude') and msg.latitude is not None:
                print('lat: ' + str(round(msg.latitude, 6)))
            if hasattr(msg, 'longitude') and msg.longitude is not None:
                print('lon: ' + str(round(msg.longitude, 6)))
            if hasattr(msg, 'altitude') and msg.altitude is not None:
                print('alt: ' + str(round(msg.altitude, 6)))
        except Exception as e:
            continue
