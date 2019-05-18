import chess.engine
import random
from reconchess import *
import os

STOCKFISH_ENV_VAR = 'STOCKFISH_EXECUTABLE'

START_MOVES = [
    # queen-side knight attacks
    # chess.Move(chess.F2, chess.F4), 
    # chess.Move(chess.E2, chess.E4), 
    # chess.Move(chess.E1, chess.F2),
    # chess.Move(chess.D2, chess.D3),
    # chess.Move(chess.G2, chess.G3),
    # chess.Move(chess.F2, chess.F3),

    # chess.Move(chess.F3, chess.E3),
    # chess.Move(chess.E3, chess.E2),
    # chess.Move(chess.E2, chess.F2)
]

square1 = chess.B5
square2 = chess.D5
square3 = chess.F5
squarelist = [square1, square2, square3]


square4 = chess.B7
square5 = chess.D7
square6 = chess.F7
king_list = [square4, square5, square6]

def flipped(square):
        return chess.square(chess.square_file(square), 7 - chess.square_rank(square))

def flipped_move(move):

    return chess.Move(from_square=flipped(move.from_square), to_square=flipped(move.to_square),
                      promotion=move.promotion, drop=move.drop)

class UberBot(Player):
    turncount = -1
    def __init__(self):
        self.move_sequence = START_MOVES
        self.kingproxy = False
        # make sure stockfish environment variable exists
        if STOCKFISH_ENV_VAR not in os.environ:
            raise KeyError(
                'TroutBot requires an environment variable called "{}" pointing to the Stockfish executable'.format(
                    STOCKFISH_ENV_VAR))

        # make sure there is actually a file
        stockfish_path = os.environ[STOCKFISH_ENV_VAR]
        if not os.path.exists(stockfish_path):
            raise ValueError('No stockfish executable found at "{}"'.format(stockfish_path))

        # initialize the stockfish engine
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)

    def handle_game_start(self, color: Color, board: chess.Board):
        if color == chess.BLACK:
            self.move_sequence = list(map(flipped_move, self.move_sequence))
        
        self.board = board
        self.color = color

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.my_piece_captured_square = capture_square
        if captured_my_piece:
            self.board.remove_piece_at(capture_square)

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        # This bot is based on a cheese strategy. The objective of this bot is to trick the other bot into making a move for
        # our king, and getting trapped as a result. 
        # We figure that the other bot places an emphasis on tunnel vision for our king, and will go after all all costs.
        # We want to counter that approach. 

        # When the king is moved into a semi-vulnerable or vulnerable position, keep a close watch on it. 
        # if (self.board.king(self.color) is None):
        #     return None
        # if self.turncount > 3 and self.board.king(self.color) != chess.E1:
        #     # Stay within 2 king moves in front of the king
        #     i = random.randint(-2,2)
        #     while True:
        #         if (chess.square_distance(self.board.king(self.color), self.board.king(self.color) + (2 + i))) > 2:
        #             i -= 1
        #         elif (chess.square_distance(self.board.king(self.color), self.board.king(self.color) + (2 + i))) < 2:
        #             i += 1
        #         else:
        #             return self.board.king(self.color) + (2 + i)
        # else:
        # if our piece was just captured, sense where it was captured
        if self.my_piece_captured_square:
            return self.my_piece_captured_square

        # if we might capture a piece when we move, sense where the capture will occur
        future_move = self.choose_move(move_actions, seconds_left)
        if future_move is not None and self.board.piece_at(future_move.to_square) is not None:
            return future_move.to_square

        # look for the king
        king_square = chess.E2
        if self.turncount % 3 == 0:
            if self.color == chess.WHITE:
                king_square = flipped(king_square)
            enemy_king_square = self.board.king(not self.color)
            if enemy_king_square:
                return king_square
            else:
                # search for the king, wherever it is
                if self.color == chess.WHITE:
                    king_square_proxy = flipped(random.choice(king_list))
                return king_square_proxy

        if self.kingproxy:
            if self.color == chess.WHITE:
                king_square_proxy = flipped(random.choice(king_list))
            return king_square_proxy

        # b5, d5, f5
        if self.color == chess.WHITE:
            return flipped(random.choice(squarelist))
        return random.choice(squarelist)

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        # add the pieces in the sense result to our board
        for square, piece in sense_result:
            self.board.set_piece_at(square, piece)

        enemy_king_square = self.board.king(not self.color)
        if not enemy_king_square:
            self.kingproxy = True
        else:
            self.kingproxy = False


    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        self.turncount += 1
        # Default pattern is to move up one pawn, then move up the king, 
        # then move up another pawn, then move the king back to saftey
        # cycle the king in a circle otherwise
        
        # if we might be able to take the king, try to
        enemy_king_square = self.board.king(not self.color)
        if enemy_king_square:
            # if there are any ally pieces that can take king, execute one of those moves
            enemy_king_attackers = self.board.attackers(self.color, enemy_king_square)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                return chess.Move(attacker_square, enemy_king_square)
        
        # otherwise, try to move with the stockfish chess engine
        try:
            self.board.turn = self.color
            self.board.clear_stack()
            result = self.engine.play(self.board, chess.engine.Limit(time=0.5))
            return result.move
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError) as e:
            print('Engine bad state at "{}"'.format(self.board.fen()))

        # if all else fails, pass
        return None


    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        # if a move was executed, apply it to our board
        if taken_move is not None:
            self.board.push(taken_move)

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        self.engine.quit()









