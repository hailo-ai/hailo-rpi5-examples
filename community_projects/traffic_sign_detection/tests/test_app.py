import pytest
from app import app_callback, user_app_callback_class
from gi.repository import Gst

def test_app_callback():
    user_data = user_app_callback_class()
    pad = Gst.Pad()
    info = Gst.PadProbeInfo()
    result = app_callback(pad, info, user_data)
    assert result == Gst.PadProbeReturn.OK
