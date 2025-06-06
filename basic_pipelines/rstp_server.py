import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')

from gi.repository import Gst, GstRtspServer, GLib

Gst.init(None)

class UdpToRtspFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self):
        super(UdpToRtspFactory, self).__init__()
        self.set_shared(True)

    def do_create_element(self, url):
        pipeline_str = (
            'udpsrc port=5000 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! '
            'rtph264depay ! rtph264pay config-interval=1 name=pay0 pt=96'
        )
        return Gst.parse_launch(f"( {pipeline_str} )")

class UdpRtspServer:
    def __init__(self):
        self.server = GstRtspServer.RTSPServer()
        factory = UdpToRtspFactory()
        mount_points = self.server.get_mount_points()
        mount_points.add_factory("/stream", factory)
        self.server.attach(None)

if __name__ == "__main__":
    print("RTSP server streaming from UDP at rtsp://<ip>:8554/stream")
    server = UdpRtspServer()
    loop = GLib.MainLoop()
    loop.run()

