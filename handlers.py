import chess
import chess.uci

class PonderHandler(chess.uci.InfoHandler):
    def __init__(self, callback):
        self.callback = callback
        super(PonderHandler, self).__init__()

    def post_info(self):
        if 1 in self.info["score"]:
            cp, mate = self.info["score"][1]
            if cp is not None: 
                cp = -cp
            if mate is not None:
                mate = -mate
            self.info["score"][1] = chess.uci.Score(cp, mate)
            self.callback(self.info)

        super(PonderHandler, self).post_info()


class InfoHandler(chess.uci.InfoHandler):
    def __init__(self, callback):
        self.callback = callback
        super(InfoHandler, self).__init__()

    def post_info(self):
        if 1 in self.info["score"]:
            self.callback(self.info)

        super(InfoHandler, self).post_info()
