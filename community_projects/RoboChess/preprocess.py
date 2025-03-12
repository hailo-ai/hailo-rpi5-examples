import sys
sys.path.append("LiveChess2Fen")

from LiveChess2Fen.lc2fen.predict_board import detect_input_board, obtain_individual_pieces
import numpy as np
import cv2


# This code receives a Frame from the camera and performs the following steps:
# 1. crops the board from the image by corner detection
# 2. crops the board to pieces.
def preprocess(numpy_frame):
    try:
        _, cropped_board = detect_input_board(numpy_frame)
    except:
        print("No board detected")
        return False, None, None
    pieces, corners = obtain_individual_pieces(cropped_board["orig"])
    pieces = np.concatenate(pieces, axis=0)
    return True, cropped_board["orig"], pieces

def main():
    img_path = "LiveChess2Fen/data/predictions/TestImages/FullDetection/test1.jpg"
    image = cv2.imread(img_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pieces = preprocess(image)
    
if __name__ == "__main__":
    main()
