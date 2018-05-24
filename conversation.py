from time import time
import os
import chess

class Conversation():
    def __init__(self, game, engines_controller, xhr, version):
        self.game = game
        self.engines_controller = engines_controller
        self.xhr = xhr
        self.version = version

    command_prefix = "!"

    def react(self, line, game):
        print("*** {} [{}] {}: {}".format(self.game.url(), line.room, line.username, line.text.encode("utf-8")))
        if (line.text[0] == self.command_prefix):
            self.command(line, game, line.text[1:].lower())
        pass

    def command(self, line, game, cmd):
        if cmd == "wait" and game.is_abortable():
            game.abort_in(60)
            self.send_reply(line, "Waiting 60 seconds...")
        elif cmd == "name":
            self.send_reply(line, "{} (lichess-bot v{})".format(self.engines_controller.playing.name(), self.version))
        elif cmd == "howto":
            self.send_reply(line, "How to run your own bot: lichess.org/api#tag/Chess-Bot")
        elif cmd == "eval" and line.room == "spectator":
            playing = self.engines_controller.playing.get_stats()
            stockfish = self.engines_controller.referee.get_stats()

            output = "Leela: score: {0}, nps: {1}, nodes: {2}" \
                .format(playing["score"][1].cp, \
                playing["nps"], \
                playing["nodes"])
            output += '\n'
            output += "Stockfish: depth: {0}, score: {1}, mate: {2}" \
                .format(stockfish["depth"], \
                stockfish["score"][1].cp, \
                stockfish["score"][1].mate)

            self.send_reply(line, output)
        elif cmd == "eval":
            self.send_reply(line, "I don't tell that to my opponent, sorry.")
        elif cmd == "id":
            self.send_reply(line, "ID " + self.engines_controller.playing.id)
        elif cmd ==  "hardware" or cmd == "gpu":
            self.send_reply(line, "Intel(R) Xeon(R) CPU E5-2630 v4 @ 2.20GHz, 20 cores, 60Gb RAM, 8xGTX1080")
        elif cmd == "leela":
            self.send_reply(line, "For mother Russia!")
        elif cmd == "stockfish" or cmd == "sf" and line.room == "spectator":
            stats = self.engines_controller.referee.get_stats()
            self.send_reply(line, \
                    "depth: {0}, score: {1}, mate: {2}" \
                        .format(stats["depth"], stats["score"][1].cp, \
                        stats["score"][1].mate))
        elif cmd == "commands":
            self.send_reply(line, "Supported commands: !howto, !name, !eval, !id, !hardware, !commands, !leela, !sf")

    def send_reply(self, line, reply):
        self.xhr.chat(self.game.id, line.room, reply)


class ChatLine():
    def __init__(self, json):
        self.room = json.get("room")
        self.username = json.get("username")
        self.text = json.get("text")
