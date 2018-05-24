with open('command.txt', 'w') as f:
    comm=[]
    gpus = [0, 1, 2, 3, 4]
    idx = 0
    cur_l = 'a'
    for i in range(len(gpus)):
        if idx == len(gpus):
            idx -= len(gpus)

        cur_comm = '{0}(backend=cudnn,gpu={1},max_batch=512)'.format(cur_l, gpus[idx])
        comm.append(cur_comm)
        idx += 1
        cur_l = chr(ord(cur_l) + 1)

    command = '[\'./engines/lc0_new\', \'--slowmover=2.8\', \'--tempdecay-moves=5\', \'--threads=20\', \'--weights=engines/weights_kb1-256x20-2100000.txt\', \'--cpuct=3.16836\', \'--fpu-reduction=-0.0683163\', \'--backend=multiplexing\', \'--nncache=20000000\', \'--backend-opts=' + ','.join(comm) + '\']'
    print(command, file=f)

with open('run_command.sh', 'w') as f:
    print(' '.join(eval(command)), file=f)
