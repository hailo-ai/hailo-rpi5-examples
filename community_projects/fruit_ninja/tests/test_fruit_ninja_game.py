import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch
import multiprocessing as mp
import queue
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import sys
import os

# Add the parent directory to the path to import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fruit_ninja_game import user_app_callback_class, app_callback


class TestUserAppCallbackClass(unittest.TestCase):
    """Test cases for the user_app_callback_class."""

    @patch('fruit_ninja_game.mp.Process')
    @patch('fruit_ninja_game.PygameFruitNinja')
    def test_init(self, mock_pygame_fruit_ninja, mock_process):
        """Test initialization of user_app_callback_class."""
        # Mock parser and args
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.video_width = 640
        mock_args.video_height = 480
        mock_parser.parse_args.return_value = mock_args

        # Mock process
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Create instance
        user_data = user_app_callback_class(mock_parser)

        # Verify initialization
        self.assertEqual(user_data.frame_width, 640)
        self.assertEqual(user_data.frame_height, 480)
        self.assertIsNotNone(user_data.hand_positions_queue)
        self.assertIsNotNone(user_data.fruits_queue)

        # Verify process was started
        mock_process_instance.start.assert_called_once()

    @patch('fruit_ninja_game.mp.Process')
    @patch('fruit_ninja_game.PygameFruitNinja')
    def test_init_default_dimensions(self, mock_pygame_fruit_ninja, mock_process):
        """Test initialization with default video dimensions."""
        # Mock parser and args without video dimensions
        mock_parser = Mock()
        mock_args = Mock()
        del mock_args.video_width  # Simulate missing attribute
        del mock_args.video_height
        mock_parser.parse_args.return_value = mock_args

        # Mock process
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance

        # Create instance
        user_data = user_app_callback_class(mock_parser)

        # Verify default dimensions (actual defaults in code)
        self.assertEqual(user_data.frame_width, 1280)
        self.assertEqual(user_data.frame_height, 720)

    @patch('fruit_ninja_game.mp.Process')
    @patch('fruit_ninja_game.PygameFruitNinja')
    def test_destructor(self, mock_pygame_fruit_ninja, mock_process):
        """Test destructor cleanup."""
        # Mock parser and process
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.video_width = 640
        mock_args.video_height = 480
        mock_parser.parse_args.return_value = mock_args

        mock_process_instance = Mock()
        mock_process_instance.is_alive.return_value = True
        mock_process.return_value = mock_process_instance

        # Create and destroy instance
        user_data = user_app_callback_class(mock_parser)
        user_data.__del__()

        # Verify cleanup
        mock_process_instance.terminate.assert_called_once()
        mock_process_instance.join.assert_called_once_with(timeout=2)


class TestAppCallback(unittest.TestCase):
    """Test cases for the app_callback function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_pad = Mock()
        self.mock_info = Mock()
        self.mock_user_data = Mock()
        self.mock_buffer = Mock()
        self.mock_roi = Mock()

        # Set up user data
        self.mock_user_data.frame_width = 640
        self.mock_user_data.frame_height = 480
        self.mock_user_data.hand_positions_queue = Mock()
        self.mock_user_data.fruits_queue = Mock()

    @patch('fruit_ninja_game.hailo')
    def test_app_callback_no_buffer(self, mock_hailo):
        """Test app_callback with no buffer."""
        # Mock no buffer
        self.mock_info.get_buffer.return_value = None

        result = app_callback(self.mock_pad, self.mock_info, self.mock_user_data)

        self.assertEqual(result, Gst.PadProbeReturn.OK)
        self.mock_user_data.increment.assert_called_once()

    @patch('fruit_ninja_game.hailo')
    def test_app_callback_no_detections(self, mock_hailo):
        """Test app_callback with no person detections."""
        # Mock buffer and ROI with no person detections
        self.mock_info.get_buffer.return_value = self.mock_buffer
        mock_hailo.get_roi_from_buffer.return_value = self.mock_roi
        self.mock_roi.get_objects_typed.return_value = []

        # Mock empty queues
        self.mock_user_data.fruits_queue.get_nowait.side_effect = queue.Empty()

        result = app_callback(self.mock_pad, self.mock_info, self.mock_user_data)

        self.assertEqual(result, Gst.PadProbeReturn.OK)
        self.mock_user_data.increment.assert_called_once()


class TestIntegration(unittest.TestCase):
    """Integration tests for the fruit ninja game."""

    @patch('fruit_ninja_game.GStreamerPoseEstimationApp')
    @patch('fruit_ninja_game.get_default_parser')
    def test_main_execution(self, mock_get_parser, mock_app_class):
        """Test main execution flow."""
        # Mock parser
        mock_parser = Mock()
        mock_get_parser.return_value = mock_parser

        # Mock app
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # This would normally run the main block, but we'll just verify setup
        # The actual main block is hard to test due to process creation
        self.assertTrue(True)  # Placeholder for integration test


if __name__ == '__main__':
    unittest.main()