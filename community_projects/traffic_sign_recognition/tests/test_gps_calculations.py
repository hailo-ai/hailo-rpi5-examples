import pytest
from gps_calculations import latest_gps_data, gps_task
import asyncio

@pytest.mark.asyncio
async def test_gps_task():
    usb_path = '/dev/ttyUSB0'  # Mock path for testing

    async def run_gps():
        await gps_task(usb_path)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_gps())
    
    assert 'latitude' in latest_gps_data
    assert 'longitude' in latest_gps_data
    assert 'altitude' in latest_gps_data
