    
import sys
import matplotlib.pyplot as plt
sys.path.append("LiveChess2Fen")

import io
from LiveChess2Fen.lc2fen.fen import board_to_fen, list_to_board
from LiveChess2Fen.lc2fen.infer_pieces import infer_chess_pieces


DRAW_FEN = True
def prop2fen(probs, a1_pos="BL", previous_fen=None, ax=None):
    prob_list = [probs[i] for i in range(probs.shape[0])]
    predictions = infer_chess_pieces(prob_list, a1_pos, previous_fen)
    board = list_to_board(predictions)
    fen = board_to_fen(board)

    if DRAW_FEN:
        import chess
        import chess.svg
        from IPython.display import SVG
        board = chess.Board(fen)
        svg_content= chess.svg.board(board)
        import cairosvg
        png_image = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
        from PIL import Image
        image = Image.open(io.BytesIO(png_image))
        ax.clear()
        ax.imshow(image)
        ax.axis('off')  # Turn off the axis
        plt.draw()
        plt.pause(0.1)  # Pause to allow the window to refresh

    return fen
