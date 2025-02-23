#!/usr/bin/env python3
import cv2
import numpy as np
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams, InputVStreamParams, OutputVStreamParams, FormatType)
from preprocess import preprocess
from postprocess import prop2fen
from next_step_calculator import calculate_next_step
import subprocess
import time
import matplotlib.pyplot as plt
from voicer import play_sound


HEF_XCEPTION_PATH = "model.hef"

purple_command = ['python', 'set_wled.py', 'half_purpel.json', '4.3.2.1']
green_command = ['python', 'set_wled.py', 'half_green.json', '4.3.2.1']


class RoboChess:
    def __init__(self, target):
        self._target = target
        self._xception_infer_vstreams = self._create_xception_infer_vstream(target)

    def _create_xception_infer_vstream(self, target):
        hef = HEF(HEF_XCEPTION_PATH)
        configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        configure_params['model'].batch_size = 64
        import ipdb; ipdb.set_trace()
        network_group = target.configure(hef, configure_params)[0]
        input_vstreams_params = InputVStreamParams.make_from_network_group(network_group, quantized=False, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make_from_network_group(network_group, quantized=False, format_type=FormatType.FLOAT32)
        return InferVStreams(network_group, input_vstreams_params, output_vstreams_params)

    def infer(self, input_data):
        with self._xception_infer_vstreams as infer_pipeline:
            network_group = self._xception_infer_vstreams._configured_net_group
            network_group_params = network_group.create_params()
            with network_group.activate(network_group_params):
                infer_results = infer_pipeline.infer(input_data)
                return infer_results

def stockfishy_fen(fen, turn='b', castling_rights='KQkq', en_passant='-', halfmove='0', fullmove='0'):
    return f"{fen} {turn} {castling_rights} {en_passant} {halfmove} {fullmove}"

def unstocfishy_fen(stockfishy_fen):
    return stockfishy_fen.split()[0]

RECORD_IMAGE = False
USE_IMAGE = False
LED = True

fig, ax = plt.subplots()

def main():
    with VDevice() as target:
        robochess = RoboChess(target)

        # Open the video capture from /dev/video0
        cap = cv2.VideoCapture('/dev/video0')

        # Check if the camera opened successfully
        if not cap.isOpened():
            print("Error: Could not open camera.")
        else:
            # Set the resolution (width and height)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            # Set the capture format to MJPEG (if supported by the camera)
            #cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        previous_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'

        halfmove = 0
        fullmove = 1

        while True:
            # Read a frame from the camera
            ret, frame = cap.read()

            # Check if the frame was successfully captured
            if ret:
                if RECORD_IMAGE:
                    cv2.imwrite('captured_image.jpg', frame)
                if USE_IMAGE:
                    frame = cv2.imread('captured_image.jpg')
                # Display the captured frame (image) continuously
                cv2.imshow("Captured Image", frame)

                # Wait for keypress
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):  # If 'q' is pressed, exit
                    break
                elif key == ord(' '):  # If spacebar is pressed, process the frame
                    if LED:
                        subprocess.run(green_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        time.sleep(1)
                    print("Processing Board")
                    # Perform the preprocessing and inference only when spacebar is pressed
                    detected, cropped_board, pieces64 = preprocess(frame)
                    if not detected:
                        continue
                    #pieces64 /= 255
                    #pieces64 -= 1
                    board_result = robochess.infer(pieces64)  # 64 on 13

                    fen = prop2fen(board_result['model/fc2'], previous_fen=previous_fen, ax=ax)
                    
                    should_recapture = False
                    while True:
                        key2 = cv2.waitKey(0) & 0xFF
                        #if key2 == ord(' '):  # If spacebar is pressed, continue
                        #    pass
                        if key2 == ord('r'):  # If 'r' is pressed, reset the loop
                            should_recapture = True
                            break
                        elif key2 == ord(' '):
                            print("Valid Capture")
                            break

                    if should_recapture:
                        print("Recapturing")
                        continue

                    #play_sound(f"Black turn to play")

                    stockfish_fen = stockfishy_fen(fen, turn='b', halfmove=str(halfmove), fullmove=str(fullmove))
                    #halfmove = halfmove + 1 % 2
                    fullmove = fullmove + 1 
                    next_move_valid, updated_fen = calculate_next_step(stockfish_fen, ax)
                    previous_fen = unstocfishy_fen(updated_fen)
                    if LED:
                        subprocess.run(purple_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    # Display the cropped board
                    #cv2.imshow("Cropped Board", cv2.resize(cropped_board, (1024,768)))

                    if next_move_valid == -1:
                        #import ipdb; ipdb.set_trace()
                        print("Bad next move")
                        continue

            else:
                print("Error: Could not read frame.")
                break

        cap.release()
        cv2.destroyAllWindows()



if __name__ == "__main__":
    main()
