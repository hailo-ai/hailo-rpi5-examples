import unittest
from unittest.mock import patch, MagicMock
from pipeline import GStreamerDetectionCropperApp

class TestGStreamerDetectionCropperApp(unittest.TestCase):

    @patch('pipeline.get_default_parser')
    @patch('pipeline.detect_hailo_arch')
    @patch('pipeline.GStreamerApp.__init__')
    def test_initialization(self, mock_gstreamer_app_init, mock_detect_hailo_arch, mock_get_default_parser):
        mock_gstreamer_app_init.return_value = None
        mock_detect_hailo_arch.return_value = 'hailo8'
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = MagicMock(
            apps_infra_path='/path/to/hailo-apps-infra',
            arch=None
        )
        mock_get_default_parser.return_value = mock_parser

        app = GStreamerDetectionCropperApp(None, None, '/path/to/app')

        self.assertEqual(app.arch, 'hailo8')
        self.assertEqual(app.depth_post_function_name, 'filter_scdepth')
        self.assertEqual(app.detection_hef_path, '/path/to/hailo-apps-infra/resources/yolov8m.hef')
        self.assertEqual(app.depth_hef_path, '/path/to/hailo-apps-infra/resources/scdepthv3.hef')

if __name__ == '__main__':
    unittest.main()
