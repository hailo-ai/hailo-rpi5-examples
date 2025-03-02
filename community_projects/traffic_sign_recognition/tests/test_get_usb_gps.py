import pytest
from unittest.mock import patch
from get_usb_gps import get_usb_gps_devices

@patch('os.listdir')
@patch('serial.Serial')
def test_get_usb_gps_devices(mock_serial, mock_listdir):
    mock_listdir.return_value = ['ttyUSB0', 'ttyUSB1']
    mock_serial.return_value.readline.return_value = '$GPGGA,123456.78,1234.56,N,12345.67,W,1,08,0.9,545.4,M,46.9,M,,*47'
    
    device = get_usb_gps_devices()
    assert device is not None
    assert '/dev/ttyUSB' in device
