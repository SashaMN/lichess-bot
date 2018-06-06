import chess
import chess.uci
import time

with open('command.txt') as f:
    command = eval(f.readline())

command.append('--no-smart-pruning')

engine = chess.uci.popen_engine(command)
engine.uci()
engine.ucinewgame()
N = 130000

print('Test started!')
start = time.time()
engine.go(nodes=N)
end = time.time()
print('Test finished!\nnps: {}'.format(N / (end - start)))
