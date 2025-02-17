from stockfish import Stockfish
import io
import chess
import cairosvg
from IPython.display import SVG
import matplotlib.pyplot as plt
from PIL import Image
from voicer import play_sound

def unstocfishy_fen(stockfishy_fen):
    return stockfishy_fen.split()[0]

def calculate_next_step(current_fen="rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", ax=None):
    # checks correctness of board
    stockfish = Stockfish("/usr/games/stockfish")
    updated_fen = None
    if stockfish.is_fen_valid(current_fen):
        stockfish.set_fen_position(current_fen)
        print("Current board:")
        print(stockfish.get_board_visual())
        best_move = stockfish.get_best_move()
        print(f"best move is {best_move}")
        stockfish.make_moves_from_current_position([best_move])

        board = chess.Board(unstocfishy_fen(current_fen))
    
        # Calculate the start and end square of the move (e.g. "e2e4" -> E2 to E4)
        start_square = chess.parse_square(best_move[:2])  # E.g. "e2" -> chess.E2
        end_square = chess.parse_square(best_move[2:])    # E.g. "e4" -> chess.E4

        #play_sound(f"next move is black from {best_move[:2]} to {best_move[2:]}")

        # Create the SVG content for the current board state, with the arrow indicating the next move
        svg_content = chess.svg.board(
            board,
            arrows=[chess.svg.Arrow(start_square, end_square, color="#0000cccc")],  # Arrow from start to end square
            size=250
        )

        # Convert the SVG to PNG using cairosvg
        png_image = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
        
        # Open the PNG image using PIL
        image = Image.open(io.BytesIO(png_image))

        # Clear the axis and update the displayed image
        ax.clear()
        
        # Display the updated image
        ax.imshow(image)
        ax.axis('off')  # Turn off the axis
        plt.draw()  # Update the plot
        plt.pause(0.1)  # Pause to allow the window to refresh

        updated_fen = stockfish.get_fen_position()
        print("Updated board:")
        print(stockfish.get_board_visual())
        #play_sound(f"White turn to play")
        return True, updated_fen
    else:
        return False, updated_fen
    
# calculate_next_step()
