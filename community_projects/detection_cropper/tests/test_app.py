import unittest
from unittest.mock import patch, MagicMock
from app import user_app_callback_class, app_callback
from gi.repository import Gst

class TestUserAppCallbackClass(unittest.TestCase):

    def test_calculate_average_depth(self):
        user_data = user_app_callback_class()
        depth_mat = [1, 2, 3, 4, 5, 100]  # Example depth values with an outlier
        average_depth = user_data.calculate_average_depth(depth_mat)
        self.assertAlmostEqual(average_depth, 3.0, places=1)

class TestAppCallback(unittest.TestCase):

    @patch('app.hailo.get_roi_from_buffer')
    def test_app_callback(self, mock_get_roi_from_buffer):
        pad = MagicMock()
        info = MagicMock()
        buffer = MagicMock()
        info.get_buffer.return_value = buffer
        user_data = MagicMock()
        user_data.frame_count = 0

        roi = MagicMock()
        detection = MagicMock()
        detection.get_label.return_value = 'person'
        detection.get_objects_typed.return_value = [MagicMock(get_id=lambda: 1)]
        roi.get_objects_typed.return_value = [detection]
        mock_get_roi_from_buffer.return_value = roi

        result = app_callback(pad, info, user_data)
        self.assertEqual(result, Gst.PadProbeReturn.OK)
        self.assertEqual(user_data.increment.call_count, 1)

if __name__ == '__main__':
    unittest.main()
