"""
	"XFeat: Accelerated Features for Lightweight Image Matching, CVPR 2024."
	https://www.verlab.dcc.ufmg.br/descriptors/xfeat_cvpr24/

    Real-time homography estimation demo. Note that scene has to be planar or just rotate the camera for the estimation to work properly.
"""
import sys
import cv2
import argparse, sys
from modules.matching_demo import MatchingDemo
import server.external.McLumk_Wheel_Sports as mclumk

def argparser():
    parser = argparse.ArgumentParser(description="Configurations for the real-time matching demo.")
    parser.add_argument('--small-model', action="store_true", help='Use small model for better performance.')
    parser.add_argument('--max_kpts', type=int, default=3_000, help='Maximum number of keypoints.')
    parser.add_argument('--cam', type=int, default=0, help='Webcam device number.')
    parser.add_argument('--video', type=str, default="", help='video path.')
    parser.add_argument('--navigate', action="store_true", help='For navigator application, Use this flag.')
    parser.add_argument('--record', action="store_true", help='Record a new route')
    parser.add_argument('--retreat', action="store_true", help='Retrace recorded path')
    parser.add_argument('--run-with-car', action="store_true", help='Ad this flag only if you want to run with a car')
    return parser.parse_args()

if __name__ == "__main__":
    args = argparser()
    if args.navigate:
        if args.run_with_car:
            mclumk.stop_robot()
        if args.record and args.retreat:
            print("Choose only one mode")
            sys.exit(0)
        elif not args.record and not args.retreat:
            print("Choose at least one mode: record or retreat")
            sys.exit(0)
        demo = MatchingDemo(args)
        cv2.namedWindow("Real-time matching", cv2.WINDOW_NORMAL)
        if args.record:
            demo.start_recording()
        elif args.retreat:
            demo.start_playback()
        cv2.destroyAllWindows()
    else:
        demo = MatchingDemo(args = argparser())
        demo.main_loop()
