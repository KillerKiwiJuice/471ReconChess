import chess.engine
import random
from reconchess import *
import os

STOCKFISH_ENV_VAR = 'STOCKFISH_EXECUTABLE'


square1 = chess.B4
square2 = chess.D4
square3 = chess.F4
squarelist = [square1, square2, square3]


square4 = chess.B7
square5 = chess.D7
square6 = chess.F7
king_list = [square4, square5, square6]

debug = True


def flipped(square):
        return chess.square(chess.square_file(square), 7 - chess.square_rank(square))


def flipped_move(move):

    return chess.Move(from_square=flipped(move.from_square), to_square=flipped(move.to_square),
                      promotion=move.promotion, drop=move.drop)


def kinghasmoved(square1, square2):
    print("the enemy's king has moved from ", square1, "to ", square2, "!") \
        if debug and square1 != square2 else 0
    return True if square1 != square2 else False


class UberBot(Player):
    turncount = -1

    def __init__(self):
        self.kingproxy = False
        self.board = None
        self.color = None
        self.my_piece_captured_square = None
        self.enemy_king_square = None
        self.lookforenemyking = True
        self.enemyking_counter = 0

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
        self.board = board
        self.color = color
        self.enemy_king_square = chess.E2
        if self.color == chess.WHITE:
            self.enemy_king_square = flipped(chess.E2)


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

        # # if our piece was just captured, sense where it was captured
        # if self.my_piece_captured_square:
        #     return self.my_piece_captured_square
        #
        # # if we might capture a piece when we move, sense where the capture will occur
        # future_move = self.choose_move(move_actions, seconds_left)
        # if future_move is not None and self.board.piece_at(future_move.to_square) is not None:
        #     return future_move.to_square
        #
        # # otherwise, just randomly choose a sense action, but don't sense on a square where our pieces are located
        # for square, piece in self.board.piece_map().items():
        #     if piece.color == self.color:
        #         sense_actions.remove(square)
        # return random.choice(sense_actions)

        if self.my_piece_captured_square:
            print("friendly piece captured at: ", self.my_piece_captured_square) if debug else 0
            self.lookforenemyking = True
            return self.my_piece_captured_square

        # if we might capture a piece when we move, sense where the capture will occur
        future_move = self.choose_move(move_actions, seconds_left)
        if future_move is not None and self.board.piece_at(future_move.to_square) is not None:
            print("future moving: ", future_move.to_square) if debug else 0
            self.lookforenemyking = True
            return future_move.to_square

        # look for the king
        if self.lookforenemyking:
            enemy_king_square = self.enemy_king_square
            if enemy_king_square:
                if kinghasmoved(enemy_king_square, self.enemy_king_square):
                    self.enemy_king_square = enemy_king_square
                print("enemy king found: ", enemy_king_square) if debug else 0
                self.enemyking_counter += 1
                if self.enemyking_counter >= 2:
                    self.lookforenemyking = False
                    self.enemyking_counter = 0
                print("Should look for enemy king?: ", self.lookforenemyking) if debug else 0
                return enemy_king_square
            else:
                # search for the king, wherever it is
                if self.color == chess.WHITE:
                    print("king square (white): ", flipped(random.choice(king_list))) if debug else 0
                    return flipped(random.choice(king_list))
                print("king square (black): ", random.choice(king_list)) if debug else 0
                return random.choice(king_list)

        # if we looked for the king and it wasn't there
        if self.kingproxy:
            king_square_proxy = random.choice(king_list)
            # if self.color == chess.WHITE:
            #     king_square_proxy = flipped(random.choice(king_list))
            print("proxy king searching at: ", king_square_proxy) if debug else 0
            self.kingproxy = False
            print("king proxy = false") if debug else 0
            return king_square_proxy

        for square in chess.SQUARES:
            if square and self.board.piece_type_at(square) == 5 and self.board.piece_at(square).color == self.color \
                        and chess.square_rank(square) >= 5:
                return square
        # for piece in self.board:
        #     if square and self.board.piece_type_at(square) == 5 and self.board.piece_at(square).color != self.color \
        #             and self.board.square_rank(square) >= 5:
        #         return square

        # b5, d5, f5
        randomchoice1 = None
        if self.color == chess.WHITE:
            randomchoice1 = flipped(random.choice(squarelist))
            print("white, searching random middle-ground square: ", randomchoice1) if debug else 0
            return flipped(random.choice(squarelist))
        print("black, searching random middle-ground square: ", randomchoice1) if debug else 0
        self.lookforenemyking = True
        return randomchoice1

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        checkmark = True
        # add the pieces in the sense result to our board
        for square, piece in sense_result:
            self.board.set_piece_at(square, piece)
            if piece and piece.piece_type == 6 and piece.color != self.color:
                checkmark = False

        # if there is no king in the scan
        if checkmark:
            print("king proxy = true") if debug else 0
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
            result = self.engine.play(self.board, chess.engine.Limit(time=1))
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









