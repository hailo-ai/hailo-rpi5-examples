import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst



def handle_rgb(map_info, width, height):
    # The copy() method is used to create a copy of the numpy array. This is necessary because the original numpy array is created from buffer data, and it does not own the data it represents. Instead, it's just a view of the buffer's data.
    return np.ndarray(shape=(height, width, 3), dtype=np.uint8, buffer=map_info.data).copy()

def handle_nv12(map_info, width, height):
    y_plane_size = width * height
    uv_plane_size = width * height // 2
    y_plane = np.ndarray(shape=(height, width), dtype=np.uint8, buffer=map_info.data[:y_plane_size]).copy()
    uv_plane = np.ndarray(shape=(height//2, width//2, 2), dtype=np.uint8, buffer=map_info.data[y_plane_size:]).copy()
    return y_plane, uv_plane

def handle_yuyv(map_info, width, height):
    return np.ndarray(shape=(height, width, 2), dtype=np.uint8, buffer=map_info.data).copy()

FORMAT_HANDLERS = {
    'RGB': handle_rgb,
    'NV12': handle_nv12,
    'YUYV': handle_yuyv,
}

def get_numpy_from_buffer(buffer, format, width, height):
    """
    Converts a GstBuffer to a numpy array based on provided format, width, and height.
    
    Args:
        buffer (GstBuffer): The GStreamer Buffer to convert.
        format (str): The video format ('RGB', 'NV12', 'YUYV', etc.).
        width (int): The width of the video frame.
        height (int): The height of the video frame.
        
    Returns:
        np.ndarray: A numpy array representing the buffer's data, or a tuple of arrays for certain formats.
    """
    # Map the buffer to access data
    success, map_info = buffer.map(Gst.MapFlags.READ)
    if not success:
        raise ValueError("Buffer mapping failed")
    
    try:
        # Handle different formats based on the provided format parameter
        handler = FORMAT_HANDLERS.get(format)
        if handler is None:
            raise ValueError(f"Unsupported format: {format}")
        return handler(map_info, width, height)
    finally:
        buffer.unmap(map_info)