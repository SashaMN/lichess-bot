with open('command.txt', 'w') as f:
    comm=[]
    gpus = [0, 1, 2, 3, 4, 5, 6, 7]
    idx = 0
    cur_l = 'a'
    for i in range(len(gpus)):
        if idx == len(gpus):
            idx -= len(gpus)

        cur_comm = '{0}(backend=cudnn,gpu={1},max_batch=512,threads=2)'.format(cur_l, gpus[idx])
        comm.append(cur_comm)
        idx += 1
        cur_l = chr(ord(cur_l) + 1)

    command = '[\'./engines/lc0\', \'--slowmover=2.8\', \'--temperature=1.0\', \'--tempdecay-moves=10\', \'--threads=20\', \'--weights=engines/weights_367.txt.gz\', \'--cpuct=3.16836\', \'--fpu-reduction=-0.0683163\', \'--backend=multiplexing\', \'--virtual-loss-bug=60\', \'--move-overhead=300\', \'--nncache=200000000\', \'--policy-softmax-temp=1.5\', \'--allowed-node-collisions=100\', \'--extra-virtual-loss=0.5\', \'--backend-opts=' + ','.join(comm) + '\']'
    print(command, file=f)

with open('run_command.sh', 'w') as f:
    print(' '.join(eval(command)), file=f)
