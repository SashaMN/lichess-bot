class EnginesController:
    def __init__(self, playing, referee):
        self.playing = playing
        self.referee = referee

    def reset(self):
        self.playing.reset()
        self.referee.reset()

    def set_board(self, board):
        self.playing.set_board(board)
        self.referee.set_board(board)

    def set_ponder(self, value):
        self.playing.set_ponder(value)

    def first_search(self, board, movetime):
        best_move = self.playing.first_search(board, movetime)
        self.referee.go_infinite(board, best_move)
        return best_move

    def search(self, board, wtime, btime, winc, binc):
        best_move  = self.playing.search(board, wtime, btime, winc, binc)
        self.referee.stop()
        self.referee.set_board(board)
        self.referee.go_infinite(board, best_move)
        return best_move

    def stop(self):
        self.playing.stop()
        self.referee.stop()

    def terminate(self):
        self.playing.terminate()
        self.referee.terminate()


