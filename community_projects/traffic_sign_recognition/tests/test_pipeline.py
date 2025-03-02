import pytest
from pipeline import GStreamerTsrApp

def test_pipeline_creation():
    def dummy_callback(pad, info, user_data):
        pass

    class DummyUserData:
        def start_gps_task(self):
            pass

    user_data = DummyUserData()
    app = GStreamerTsrApp(dummy_callback, user_data)
    pipeline_string = app.get_pipeline_string()
    assert 'source' in pipeline_string
    assert 'inference_wrapper_detection' in pipeline_string
    assert 'tracker' in pipeline_string
    assert 'display' in pipeline_string
