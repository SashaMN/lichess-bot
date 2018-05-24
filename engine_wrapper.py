import os
import chess
import chess.xboard
import chess.uci
import handlers
import backoff
import subprocess
import copy

@backoff.on_exception(backoff.expo, BaseException, max_time=120)
def create_engine(config, board):
    cfg = config["engine"]
    engine_path = os.path.join(cfg["dir"], cfg["name"])
    engine_type = cfg.get("protocol")
    lczero_options = cfg.get("lczero")
    commands = [engine_path]
    if lczero_options:
        if "weights" in lczero_options:
            commands.append("-w")
            commands.append(lczero_options["weights"])
        if "threads" in lczero_options:
            commands.append("-t")
            commands.append(str(lczero_options["threads"]))
        if "gpu" in lczero_options:
            commands.append("--gpu")
            commands.append(str(lczero_options["gpu"]))
        if "tempdecay" in lczero_options:
            commands.append("--tempdecay")
            commands.append(str(lczero_options["tempdecay"]))
        if lczero_options.get("noise"):
            commands.append("--noise")
        if "log" in lczero_options:
            commands.append("--logfile")
            commands.append(lczero_options["log"])

    with open('command.txt') as f:
        commands = eval(f.readline())
    silence_stderr = cfg.get("silence_stderr", False)

    if engine_type == "xboard":
        return XBoardEngine(board, commands, cfg.get("xboard_options", {}) or {}, silence_stderr)

    return UCIEngine(board, commands, cfg.get("uci_options", {}) or {}, silence_stderr)


class EngineWrapper:

    def __init__(self, board, commands, options=None, silence_stderr=False):
        pass

    def set_time_control(self, game):
        pass

    def first_search(self, board, movetime):
        pass

    def search(self, board, wtime, btime, winc, binc):
        pass

    def print_stats(self):
        pass

    def name(self):
        return self.engine.name

    def quit(self):
        self.engine.quit()

    def print_handler_stats(self, info, stats):
        for stat in stats:
            if stat in info:
                print("    {}: {}".format(stat, info[stat]))

    def get_handler_stats(self, info, stats):
        result = {}
        for stat, value in info.items():
            if stat in info:
                result[stat] = value

        return result


class UCIEngine(EngineWrapper):
    def __init__(self, board, commands, options={}, silence_stderr=False):
        commands = commands[0] if len(commands) == 1 else commands
        self.go_commands = options.get("go_commands", {})

        self.engine = chess.uci.popen_engine(commands, stderr = subprocess.DEVNULL if silence_stderr else None)
        self.engine.uci()

        if options:
            self.engine.setoption(options)

        self.engine.setoption({
            "UCI_Variant": type(board).uci_variant,
            "UCI_Chess960": board.chess960
        })
        self.set_board(board)

        self.ponder_handler = handlers.PonderHandler(self.change_info)
        self.info_handler = handlers.InfoHandler(self.change_info)

        self.engine.info_handlers.append(self.info_handler)

        weights_command = ''
        for command in commands:
            if command.find("weights") != -1:
                weights_command = command
                break
        prefix = "weights_"
        suffix = ".txt"
        startpos = weights_command.find(prefix) + len(prefix)
        endpos = weights_command.find(suffix)
        self.id = weights_command[startpos:endpos]
        self.reset()

    def change_info(self, info):
        if "fish" in self.engine.name:
            self.info = info
            return

        if self.info is None:
            self.info = copy.deepcopy(info)
            return

        alpha = 0.99
        if 1 in self.info["score"] and \
                "nps" in info and \
                "nodes" in info:
            old_nps = self.info["nps"]
            old_nodes = self.info["nodes"]

            self.info = copy.deepcopy(info)
            self.info["nps"] = \
                round(old_nps * alpha + info["nps"] * (1.0 - alpha))
            output = "Leela: score: {0}, nps: {1}, nodes: {2}" \
                .format(self.info["score"][1].cp, \
                self.info["nps"], \
                self.info["nodes"])
            if old_nodes > self.info["nodes"]:
                nodes_reused = self.info["nodes"] / old_nodes * 100.0
                self.nodes_reused_history.append(nodes_reused)
                output += ", reused: {0:.2f}%, avg. reused: {1:.2f}%" \
                        .format(nodes_reused,
                                sum(self.nodes_reused_history) / \
                                len(self.nodes_reused_history))
            print(output)

    def reset(self):
        self.engine.ucinewgame()
        self.set_ponder(True)
        self.info = None
        self.nodes_reused_history = []

    def set_board(self, board):
        self.engine.position(board)

    def set_ponder(self, value):
        if not value:
            self.stop()
        self.ponder = value

    def first_search(self, board, movetime):
        self.engine.position(board)
        best_move, _ = self.engine.go(movetime=movetime)
        self.go_infinite(board, best_move)
        return best_move

    def search(self, board, wtime, btime, winc, binc):
        self.stop()
        self.set_board(board)
        cmds = self.go_commands
        if self.engine.info_handlers:
            self.engine.info_handlers.pop()
            self.engine.info_handlers.append(self.info_handler)
        best_move, _ = self.engine.go(
            wtime=wtime,
            btime=btime,
            winc=winc,
            binc=binc,
            depth=cmds.get("depth"),
            nodes=cmds.get("nodes"),
            movetime=cmds.get("movetime")
        )
        self.go_infinite(board, best_move)
        return best_move

    def go_infinite(self, board, best_move):
        new_board = board.copy()
        new_board.push(best_move)
        self.set_board(new_board)
        if self.engine.info_handlers:
            self.engine.info_handlers.pop()
            self.engine.info_handlers.append(self.ponder_handler)
        if self.ponder:
            self.engine.go(
                    infinite=True,
                    async_callback=True)

    def stop(self):
        self.engine.stop()

    def terminate(self):
        self.engine.terminate()

    def print_stats(self):
        self.print_handler_stats(self.engine.info_handlers[0].info, ["string", "depth", "nps", "nodes", "score"])

    def get_stats(self):
        return self.info

class XBoardEngine(EngineWrapper):

    def __init__(self, board, commands, options=None, silence_stderr=False):
        commands = commands[0] if len(commands) == 1 else commands
        self.engine = chess.xboard.popen_engine(commands, stdout = sys.stdout)

        self.engine.xboard()

        if board.chess960:
            self.engine.send_variant("fischerandom")
        elif type(board).uci_variant != "chess":
            self.engine.send_variant(type(board).uci_variant)

        if options:
            self._handle_options(options)

        self.engine.setboard(board)

        post_handler = chess.xboard.PostHandler()
        self.engine.post_handlers.append(post_handler)

    def _handle_options(self, options):
        for option, value in options.items():
            if option == "memory":
                self.engine.memory(value)
            elif option == "cores":
                self.engine.cores(value)
            elif option == "egtpath":
                for egttype, egtpath in value.items():
                    try:
                        self.engine.egtpath(egttype, egtpath)
                    except EngineStateException:
                        # If the user specifies more TBs than the engine supports, ignore the error.
                        pass
            else:
                try:
                    self.engine.features.set_option(option, value)
                except EngineStateException:
                    pass

    def set_time_control(self, game):
        minutes = game.clock_initial / 1000 / 60
        seconds = game.clock_initial / 1000 % 60
        inc = game.clock_increment / 1000
        self.engine.level(0, minutes, seconds, inc)

    def first_search(self, board, movetime):
        self.engine.setboard(board)
        self.engine.level(0, 0, movetime / 10000, 0)
        bestmove = self.engine.go()

        return bestmove

    def search(self, board, wtime, btime, winc, binc):
        self.engine.setboard(board)
        if board.turn == chess.WHITE:
            self.engine.time(wtime / 10)
            self.engine.otim(btime / 10)
        else:
            self.engine.time(btime / 10)
            self.engine.otim(wtime / 10)
        return self.engine.go()

    def print_stats(self):
        self.print_handler_stats(self.engine.post_handlers[0].post, ["depth", "nodes", "score"])

    def get_stats(self):
        return self.get_handler_stats(self.engine.post_handlers[0].post, ["depth", "nodes", "score"])


    def name(self):
        try:
            return self.engine.features.get("myname")
        except:
            return None
