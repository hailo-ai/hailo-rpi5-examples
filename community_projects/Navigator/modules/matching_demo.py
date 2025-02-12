import cv2
import numpy as np
from modules.frame_grabber import FrameGrabber
from modules.image_recorder import ImageRecorder
from time import sleep, time
from modules.xfeat import XFeat
from modules.method import Method, CVWrapper
import os
import server.external.McLumk_Wheel_Sports as mclumk


class MatchingDemo:
    def __init__(self, args):
        self.args = args
        if args.video != "":
            self.cap = cv2.VideoCapture(args.video)
        else:
            self.cap = cv2.VideoCapture(args.cam)
        self.width = 640
        self.height = 480
        if args.small_model:
            self.width = 320
            self.height = 224
        self.ref_frame = None
        self.ref_precomp = [[],[]]
        self.corners = [[50, 50], [self.width-50, 50], [self.width-50, self.height-50], [50, self.height-50]]
        self.current_frame = None
        self.H = None
        self.setup_camera()

        #Init frame grabber thread
        self.frame_grabber = FrameGrabber(self.cap, self.width, self.height)
        self.frame_grabber.start()

        #recorder
        if args.navigate:
            self.recorder = ImageRecorder(frame_grabber=self.frame_grabber, storage_dir="resources/recorded_images")
            self.recorder.start()

        #Homography params
        self.min_inliers = 50
        self.ransac_thr = 4.0

        self.win = False

        #FPS check
        self.FPS = 0
        self.time_list = []
        self.max_cnt = 30 #avg FPS over this number of frames

        #Set local feature method here -- we expect cv2 or Kornia convention
        self.method = init_method(max_kpts=args.max_kpts, width= self.width, height=self.height)
        
        # Setting up font for captions
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.9
        self.line_type = cv2.LINE_AA
        self.line_color = (0,255,0)
        self.line_thickness = 3

        self.window_name = "Real-time matching"
        self.prev_compute = None
        
        # Removes toolbar and status bar
        cv2.namedWindow(self.window_name, flags=cv2.WINDOW_GUI_NORMAL)
        # Set the window size
        cv2.resizeWindow(self.window_name, self.width*2, self.height*2)
        #Set Mouse Callback
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

    def setup_camera(self):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        #self.cap.set(cv2.CAP_PROP_EXPOSURE, 200)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            print("Cannot open camera")
            exit()

    def draw_quad(self, frame, point_list):
        if len(self.corners) > 1:
            for i in range(len(self.corners) - 1):
                cv2.line(frame, tuple(point_list[i]), tuple(point_list[i + 1]), self.line_color, self.line_thickness, lineType = self.line_type)
            if len(self.corners) == 4:  # Close the quadrilateral if 4 corners are defined
                cv2.line(frame, tuple(point_list[3]), tuple(point_list[0]), self.line_color, self.line_thickness, lineType = self.line_type)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.corners) >= 4:
                self.corners = []  # Reset corners if already 4 points were clicked
            self.corners.append((x, y))

    def putText(self, canvas, text, org, fontFace, fontScale, textColor, borderColor, thickness, lineType):
        # Draw the border
        cv2.putText(img=canvas, text=text, org=org, fontFace=fontFace, fontScale=fontScale, 
                    color=borderColor, thickness=thickness+2, lineType=lineType)
        # Draw the text
        cv2.putText(img=canvas, text=text, org=org, fontFace=fontFace, fontScale=fontScale, 
                    color=textColor, thickness=thickness, lineType=lineType)

    def warp_points(self, points, H, x_offset = 0):
        points_np = np.array(points, dtype='float32').reshape(-1,1,2)

        warped_points_np = cv2.perspectiveTransform(points_np, H).reshape(-1, 2)
        warped_points_np[:, 0] += x_offset
        warped_points = warped_points_np.astype(int).tolist()
        
        return warped_points

    def create_top_frame(self):
        top_frame_canvas = np.zeros((self.height, self.width*2, 3), dtype=np.uint8)
        top_frame = np.hstack((self.ref_frame, self.current_frame))
        color = (3, 186, 252)
        cv2.rectangle(top_frame, (2, 2), (self.width*2-2, self.height-2), color, 5)  # Orange color line as a separator
        top_frame_canvas[0:self.height, 0:self.width*2] = top_frame
        
        # Adding captions on the top frame canvas
        self.putText(canvas=top_frame_canvas, text="Reference Frame:", org=(10, 30), fontFace=self.font, 
            fontScale=self.font_scale, textColor=(0,0,0), borderColor=color, thickness=1, lineType=self.line_type)

        self.putText(canvas=top_frame_canvas, text="Target Frame:", org=(self.width+10, 30), fontFace=self.font, 
                    fontScale=self.font_scale,  textColor=(0,0,0), borderColor=color, thickness=1, lineType=self.line_type)
        
        self.draw_quad(top_frame_canvas, self.corners)
        
        return top_frame_canvas

    def get_area_mid(self, points):
        X = 0
        Y = 1
        top_left = 0
        top_right = 1
        bottom_right = 2
        bottom_left = 3

        height = points[bottom_right][Y] - points[top_right][Y]
        width = points[top_right][X] - points[top_left][X]
        area = height * width

        midx = points[top_left][X] + (width / 2)
        midy = points[top_left][X] + (height / 2)

        return area, midx, midy

    def print_directions(self, points, ref_points):
        area, midx, midy = self.get_area_mid(points)
        ref_area, ref_midx, ref_midy = self.get_area_mid(ref_points)
        midx -= self.width

        area_threshold = 0.22
        midx_threshold = 0.5
        speed_default = 5

        if ((1 - midx_threshold) < abs(midx / ref_midx) < (1 + midx_threshold)):
            if ((1 - area_threshold) < abs(area / ref_area) < (1 + area_threshold)):
                # Robot is in the right spot, next image
                self.ref_frame = self.recorder.get_next_image()
                if self.ref_frame is None:
                    print("Reached destination")
                    self.win = True
                    return
                self.ref_precomp = self.method.descriptor.detectAndCompute(self.ref_frame, None)
            elif area < ref_area:
                if self.args.run_with_car:
                    mclumk.move_forward(speed_default)
                sleep(1)
                print("Forward")
            else:
                if self.args.run_with_car:
                    mclumk.move_backward(speed_default)
                sleep(1)
                print("Backward")
        elif midx < ref_midx:
            if self.args.run_with_car:
                mclumk.rotate_left(3)
            sleep(0.5)
            print("Left")
        else:
            if self.args.run_with_car:
                mclumk.rotate_right(3)
            sleep(0.5)
            print("Right")

        if self.args.run_with_car:
            mclumk.stop_robot()

    def process(self):
        # Create a blank canvas for the top frame
        top_frame_canvas = self.create_top_frame()

        # Match features and draw matches on the bottom frame
        bottom_frame = self.match_and_draw(self.ref_frame, self.current_frame)
        # Draw warped corners
        if self.H is not None and len(self.corners) > 1:
            if self.args.navigate:
                self.print_directions(self.warp_points(self.corners, self.H, self.width), self.corners)
            self.draw_quad(top_frame_canvas, self.warp_points(self.corners, self.H, self.width))
        elif self.args.navigate:
            if self.args.run_with_car:
                mclumk.stop_robot()
            print("No box!!!!")

        key = cv2.waitKey(1)

        # Stack top and bottom frames vertically on the final canvas
        canvas = np.vstack((top_frame_canvas, bottom_frame))

        cv2.imshow(self.window_name, canvas)

    def match_and_draw(self, ref_frame, current_frame):
        bad_threshold = 10
        if self.args.navigate:
            bad_threshold = 60
        matches, good_matches = [], []
        kp1, kp2 = [], []
        points1, points2 = [], []


        current = self.method.descriptor.detectAndCompute(current_frame)
        # end = time()
        # print(end-start)
        kpts1, descs1 = self.ref_precomp['keypoints'], self.ref_precomp['descriptors']
        kpts2, descs2 = current['keypoints'], current['descriptors']
        if len(kpts1) == 0 or len(kpts2) == 0:
            return np.hstack([ref_frame, current_frame])
        idx0, idx1 = self.method.matcher.match(descs1, descs2, 0.82)
        points1 = kpts1[idx0].cpu().numpy()
        points2 = kpts2[idx1].cpu().numpy()

        if len(points1) > bad_threshold and len(points2) > bad_threshold:
            # Find homography
            self.H, inliers = cv2.findHomography(points1, points2, cv2.USAC_MAGSAC, self.ransac_thr, maxIters=700, confidence=0.995)
            inliers = inliers.flatten() > 0
            
            if inliers.sum() < self.min_inliers:
                self.H = None


            kp1 = [cv2.KeyPoint(p[0],p[1], 5) for p in points1[inliers]]
            kp2 = [cv2.KeyPoint(p[0],p[1], 5) for p in points2[inliers]]
            good_matches = [cv2.DMatch(i,i,0) for i in range(len(kp1))]
            
            # Draw matches
            matched_frame = cv2.drawMatches(ref_frame, kp1, current_frame, kp2, good_matches, None, matchColor=(0, 200, 0), flags=2)
            
        else:
            matched_frame = np.hstack([ref_frame, current_frame])
            if self.args.navigate:
                return None

        color = (240, 89, 169)

        # Add a colored rectangle to separate from the top frame
        cv2.rectangle(matched_frame, (2, 2), (self.width*2-2, self.height-2), color, 5)

        # Adding captions on the top frame canvas
        self.putText(canvas=matched_frame, text="%s Matches: %d"%('XFeat', len(good_matches)), org=(10, 30), fontFace=self.font, 
            fontScale=self.font_scale, textColor=(0,0,0), borderColor=color, thickness=1, lineType=self.line_type)
        
                # Adding captions on the top frame canvas
        self.putText(canvas=matched_frame, text="", org=(self.width+10, 30), fontFace=self.font, 
            fontScale=self.font_scale, textColor=(0,0,0), borderColor=color, thickness=1, lineType=self.line_type)

        return matched_frame
    
    """main API functions: start_playback, start_recording, stop recording"""
    def start_playback(self):
        self.recorder.switch_to_playback()
        self.ref_frame = self.recorder.get_next_image()
        self.ref_precomp = self.method.descriptor.detectAndCompute(self.ref_frame, None)

        while not self.win:
            self.current_frame = self.frame_grabber.get_last_frame()
            if self.current_frame is None:
                print("frame is none, bye")
                break

            self.process()
            
        self.cleanup()

    def is_folder_empty(self, folder_path):
        return len(os.listdir(folder_path)) == 0

    def start_recording(self):
        if not self.is_folder_empty('resources/recorded_images'):
            print("Warning - The recorded images folder is not empty. The recorded images will be added to the older once.")
        self.recorder.switch_to_record()
        
    def stop_recording(self):
        self.recorder.switch_to_playback()

    def main_loop(self):
        self.current_frame = self.frame_grabber.get_last_frame()
        self.ref_frame = self.current_frame.copy()
        self.ref_precomp = self.method.descriptor.detectAndCompute(self.ref_frame, None) #Cache ref features

        while True:
            if self.current_frame is None:
                break

            t0 = time()
            self.process()
            # self.match_and_draw_visual_flow(self.current_frame)
            key = cv2.waitKey(1)
            if key == ord('q'):
                break
            elif key == ord('s'):
                self.ref_frame = self.current_frame.copy()  # Update reference frame
                self.ref_precomp = self.method.descriptor.detectAndCompute(self.ref_frame, None) #Cache ref features

            self.current_frame = self.frame_grabber.get_last_frame()

            #Measure avg. FPS
            self.time_list.append(time()-t0)
            if len(self.time_list) > self.max_cnt:
                self.time_list.pop(0)
            self.FPS = 1.0 / np.array(self.time_list).mean()
        
        self.cleanup()

    def cleanup(self):
        self.recorder.stop()
        self.frame_grabber.stop()
        self.cap.release()
        cv2.destroyAllWindows()
        if self.args.run_with_car:
            mclumk.stop_robot()
    
    def draw_lines(image, all_matchs, thickness=3):
        for match in all_matchs:
            points1 = match[0]
            points2 = match[1]
            # import ipdb; ipdb.set_trace()
            sum_distance = 0
            avrg_distance = 0
            num_points = 0
            for point1, point2 in zip(points1, points2):
                euclidea_distance_2d = np.linalg.norm(np.array(point1) - np.array(point2))
                if num_points < 10 or 3*avrg_distance > euclidea_distance_2d:
                    image = cv2.line(image, (int(point1[0]),int(point1[1])), (int(point2[0]),int(point2[1])), (int(np.clip(50+euclidea_distance_2d*3, 0,255)), int(50+euclidea_distance_2d), int(np.clip(euclidea_distance_2d*3, 0,255))), thickness)
                    sum_distance += euclidea_distance_2d
                    num_points += 1
                    avrg_distance = sum_distance/num_points
        return image
    
    def match_and_draw_visual_flow(self, current_frame):
        start = time()
        if self.prev_compute is None:
            points_flow1 ,points_flow2, self.prev_compute, _null =self.method.descriptor.mtd.match_xfeat_star(np.copy(current_frame), self.frame_grabber.get_last_frame()) 
        else:
            points_flow1 ,points_flow2, self.prev_compute =self.method.descriptor.mtd.match_xfeat_star_bootstrap(self.prev_compute, np.copy(current_frame))
        
        print("Time to match: ", time()-start)
        start = time()
        self.matchs_cash.add_match([points_flow1, points_flow2])
        image = draw_lines(np.copy(current_frame), self.matchs_cash.get_matchs())
        print("Time to draw: ", time()-start)
        cv2.imshow("matches", image)
        cv2.waitKey(1)

def init_method(max_kpts, width, height):
    return Method(descriptor=CVWrapper(XFeat(top_k = max_kpts, width=width, height=height, device='hailo')), matcher=XFeat(width=width, height=height, device='hailo'))

