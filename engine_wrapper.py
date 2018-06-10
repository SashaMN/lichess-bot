import os
import chess
import chess.xboard
import chess.uci
import colors
import copy
import backoff
import handlers
import math
import subprocess

@backoff.on_exception(backoff.expo, BaseException, max_time=120)
def create_engine(config, board):
    cfg = config["engine"]
    engine_path = os.path.join(cfg["dir"], cfg["name"])
    engine_type = cfg.get("protocol")
    lczero_options = cfg.get("lczero")
    commands = [engine_path]
    # if lczero_options:
    #     if "weights" in lczero_options:
    #         commands.append("-w")
    #         commands.append(lczero_options["weights"])
    #     if "threads" in lczero_options:
    #         commands.append("-t")
    #         commands.append(str(lczero_options["threads"]))
    #     if "gpu" in lczero_options:
    #         commands.append("--gpu")
    #         commands.append(str(lczero_options["gpu"]))
    #     if "tempdecay-moves" in lczero_options:
    #         commands.append("--tempdecay-moves={}".format(lczero_options["tempdecay-moves"]))
    #         commands.append("--temperature=1.5")
    #     if lczero_options.get("noise"):
    #         commands.append("--noise")
    #     if "log" in lczero_options:
    #         commands.append("-l")
    #         commands.append(lczero_options["log"])
    #     if "nncache" in lczero_options:
    #         commands.append("--nncache={}".format(lczero_options["nncache"]))
    #     if "fpu-reduction" in lczero_options:
    #         commands.append("--fpu-reduction={}".format(lczero_options["fpu-reduction"]))
    #     if "cpuct" in lczero_options:
    #         commands.append("--cpuct={}".format(lczero_options["cpuct"]))
    
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

    def name(self):
        return self.engine.name

    def quit(self):
        self.engine.quit()

    def get_handler_stats(self, info, stats):
        if self.is_ponder:
            return self.stats_info

        self.stats_info = []
        for stat in stats:
            if stat in info:
                str = "{}: {}".format(stat, info[stat])
                if stat == "score":
                    for k,v in info[stat].items():
                        feval = 0.322978*math.atan(0.0034402*v.cp) + 0.5
                        str = "win %: {:.2f}".format(feval*100)
                self.stats_info.append(str)

        return self.stats_info


class UCIEngine(EngineWrapper):

    def __init__(self, board, commands, options, silence_stderr=False):
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
        self.engine.position(board)

        self.info_handler = handlers.InfoHandler(self.change_info)
        self.engine.info_handlers.append(self.info_handler)
        self.stats_info = []
        self.is_ponder = False

    def change_info(self, info):
        if self.info is None:
            self.info = copy.deepcopy(info)
            return
        alpha = 0.85
        if 1 in self.info["score"] and \
            "nps" in info and \
            "nodes" in info:
            old_nps = self.info["nps"]
            old_nodes = self.info["nodes"]
            
            self.info = copy.deepcopy(info)
            self.info["nps"] = \
                    round(old_nps * alpha + info["nps"] * (1.0 - alpha))
            score = self.info["score"][1].cp
            if score < 0:
                str_score = colors.CRED + str(score) + colors.CEND
            else:
                str_score = colors.CGREEN + str(score) + colors.CEND
            output = "score: {0}, nps: {1}, nodes: {2}, seldepth: {3}" \
                .format(str_score,
                        colors.CBLUE + str(self.info["nps"]) + colors.CEND,
                        colors.CBLUE + str(self.info["nodes"]) + colors.CEND,
                        colors.CBLUE + str(self.info["seldepth"]) + colors.CEND)
            if self.compute_reuse:
                self.compute_reuse = False
                nodes_reused = self.info["nodes"] / old_nodes * 100.0
                self.nodes_reused_history.append(nodes_reused)
                output += ", reused: {0}%, avg. reused: {1}%".format(
                        colors.CBLUE + str(round(nodes_reused)) + colors.CEND,
                        colors.CBLUE + \
                                str(round(sum(self.nodes_reused_history) / \
                                    len(self.nodes_reused_history))) + \
                        colors.CEND)
            print(output)

    def first_search(self, board, movetime):
        self.engine.position(board)
        best_move, _ = self.engine.go(movetime=movetime)
        return best_move


    def search(self, board, wtime, btime, winc, binc):
        self.compute_reuse = True
        self.engine.setoption({"UCI_Variant": type(board).uci_variant})
        self.engine.position(board)
        cmds = self.go_commands
        best_move, _ = self.engine.go(
            wtime=wtime,
            btime=btime,
            winc=winc,
            binc=binc,
            depth=cmds.get("depth"),
            nodes=cmds.get("nodes"),
            movetime=cmds.get("movetime")
        )
        return best_move

    def ponder(self, board):
        self.is_ponder = True
        self.engine.setoption({"UCI_Variant": type(board).uci_variant})
        board = board.copy()
        if board.move_stack:
            last_move = board.pop()
        else:
            last_move = None
        self.engine.position(board)
        ponder = self.engine.go(searchmoves=[last_move,],
                                infinite=True, async_callback=True)

    def set_board(self, board):
        self.engine.position(board)

    def stop(self):
        self.engine.stop()
        self.is_ponder = False

    def reset(self):
        self.info = None
        self.nodes_reused_history = []
        self.compute_reuse = False


    def get_stats(self):
        return self.get_handler_stats(self.engine.info_handlers[0].info, ["depth", "nps", "nodes", "score"])


class XBoardEngine(EngineWrapper):

    def __init__(self, board, commands, options=None, silence_stderr=False):
        commands = commands[0] if len(commands) == 1 else commands
        self.engine = chess.xboard.popen_engine(commands, stderr = subprocess.DEVNULL if silence_stderr else None)

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
        self.engine.level(0, 0, movetime / 1000, 0)
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

    def get_stats(self):
        return self.get_handler_stats(self.engine.post_handlers[0].post, ["depth", "nodes", "score"])


    def name(self):
        try:
            return self.engine.features.get("myname")
        except:
            return None
