import asyncio
import pynmea2
import serial
import io

latest_gps_data = {
    'latitude': 0,
    'longitude': 0,
    'altitude': 0
}

async def gps_task(usb_path):
    global latest_gps_data
    try:
        ser = serial.Serial(usb_path, 9600, timeout=1.0)  # parse data, wait & collect new data for 1 second, then parse buffered
        sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
    except serial.SerialException as e:
        # print(f"Error opening serial port: {e}")
        ser = None

    while True:
        try:
            if ser and ser.is_open:
                line = sio.readline()
                msg = pynmea2.parse(line)
                if hasattr(msg, 'latitude') and msg.latitude is not None and hasattr(msg, 'longitude') and msg.longitude is not None:
                    latest_gps_data['latitude'] = round(msg.latitude, 6)
                    latest_gps_data['longitude'] = round(msg.longitude, 6)
                if hasattr(msg, 'altitude') and msg.altitude is not None:
                    latest_gps_data['altitude'] = int(msg.altitude)
            else:
                # Set default values if serial data is not available
                latest_gps_data['latitude'] = 0
                latest_gps_data['longitude'] = 0
                latest_gps_data['altitude'] = 0
        except Exception as e:
            # print(f"Error reading from serial port: {e}")
            # Set default values in case of an error
            latest_gps_data['latitude'] = 0
            latest_gps_data['longitude'] = 0
            latest_gps_data['altitude'] = 0
        await asyncio.sleep(1)  # small sleep to allow other tasks to run

async def main(usb_path):
    gps = asyncio.create_task(gps_task(usb_path))
    # add other tasks here
    await gps

if __name__ == "__main__":
    usb_path = '/dev/ttyUSB0'  # or any other path to the USB GPS device
    asyncio.run(main(usb_path))
    while 1:
        print(latest_gps_data)
