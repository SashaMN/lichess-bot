with open('command.txt', 'w') as f:
    comm=[]
    gpus = [0, 1, 2, 3]
    idx = 0
    cur_l = 'a'
    for i in range(len(gpus)):
        if idx == len(gpus):
            idx -= len(gpus)

        cur_comm = '{0}(backend=cudnn,gpu={1},max_batch=512,threads=2)'.format(cur_l, gpus[idx])
        comm.append(cur_comm)
        idx += 1
        cur_l = chr(ord(cur_l) + 1)

    command = '[\'/home/anmihajlov/lichess/youngleela/engines/lc0_test\', \'--temperature=0.5\', \'--tempdecay-moves=5\', \'--threads=20\', \'--weights=/home/anmihajlov/lichess/youngleela/engines/weights_27.txt.gz\', \'--cpuct=3.6\', \'--fpu-reduction=0.85\', \'--backend=multiplexing\', \'--move-overhead=70\', \'--policy-softmax-temp=2.3\', \'--allowed-node-collisions=32\', \'--backend-opts=' + ','.join(comm) + '\']'
    print(command, file=f)

command = eval(command)
command[-1] = '\"' + command[-1] + '\"'

with open('run_command.sh', 'w') as f:
    print(' '.join(command), file=f)
