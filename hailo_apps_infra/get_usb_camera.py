import os
import subprocess

# if udevadm is not installed, install it using the following command:
# sudo apt-get install udev


def get_usb_video_devices():
    """
    Get a list of video devices that are connected via USB and have video capture capability.
    """
    video_devices = [f'/dev/{device}' for device in os.listdir('/dev') if device.startswith('video')]
    usb_video_devices = []

    for device in video_devices:
        try:
            # Use udevadm to get detailed information about the device
            udevadm_cmd = ["udevadm", "info", "--query=all", "--name=" + device]
            result = subprocess.run(udevadm_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode('utf-8')

            # Check if the device is connected via USB and has video capture capabilities
            if "ID_BUS=usb" in output and ":capture:" in output:
                usb_video_devices.append(device)
        except Exception as e:
            print(f"Error checking device {device}: {e}")

    return usb_video_devices

def main():
    usb_video_devices = get_usb_video_devices()

    if usb_video_devices:
        print(f"USB cameras found on: {', '.join(usb_video_devices)}")
    else:
        print("No available USB cameras found.")

if __name__ == "__main__":
    main()
