from subprocess import Popen
import os, time, argparse, shutil

parser = argparse.ArgumentParser(description='Runs a series of models with set configurations')
parser.add_argument('--production', action='store_true',
                        help='Production mode: If true run in a separate folder on a copy of the python scripts')

args = parser.parse_args()

# name generated by for loop...
epochs = [75]
batch_sizes = [2, 10, 32]
lrs = [1e-4, 1e-5]
momentums = [0.9]
vals = [0.1]
seeds = [0]
total_imageses = [10, 100, 1000]
net_sizes = [[1,128,256,512,1024]]

# newer ones
test = '' # Switch to --test when testing
network = 1
datasets = ['weights1', 'weights5', 'weights7']

script = 'main.py'
folder = ""
out_file = 'runs.txt'

if args.production:
    # Store the run (and scripts etc) in a month/day/ folder
    folder = 'experiments/' + time.strftime("%m_%d_%H_%M/")
    out_file = folder + out_file
    if not os.path.exists(folder):
        os.makedirs(folder)

    files_to_copy = ['run_model.py', script, 'model.py', 'model_loops.py', 'nc.py', 'data.py', 'node.py']

    for file in files_to_copy:
        shutil.copy2(file, folder)
    script = folder + script

# TODO : add profiling (torch.profiler) from pip install pytorch_tb_profiler or w/e
# TODO : run models that produce a 1024x4 (or however many) output.. which is then turned into the full size?
    # or find papers that create a weight matrix
# TODO : add a dataset (for a non declarative network) to learn the weights matrix (e.g. guassian blur weights..)

i=0
for epoch in epochs:
    for batch_size in batch_sizes:
        for lr in lrs:
            for total_images in total_imageses:
                if batch_size > total_images:
                    continue
                for net_size in net_sizes:
                    for dataset in datasets:
                        i += 1

                        run_name = 'weightsRuns' + str(i)
                        command = ["python", script, 
                                    "-n", folder + str(run_name),
                                    "-e", str(epoch),
                                    "-b", str(batch_size),
                                    "-lr", str(lr),
                                    "-ti", str(total_images),
                                    "-ns", str(net_size[0]), str(net_size[1]), str(net_size[2]),  str(net_size[3]), str(net_size[4]),
                                    "-gpu", str(1), # GPU-1 (hardcoded) is the assigned gpu for this research
                                    "--production", str(args.production),
                                    "--network", str(network),
                                    "--dataset", dataset
                                    ] 
                                    # "-m", momentum,
                                    # "-v", val,
                                    # "-s", seed,
                                    # ""]
                        print(command)
                        f = open(out_file, "a")
                        f.write(run_name + ' ' + str(command))
                        f.close()
                        p = Popen(command)
                        (output, err) = p.communicate()

# Was also run on larger models, except they were all the 300 model.
# also these may have been run on AbstractDeclarativeNode instead of EqConstrainedDeclarativeNode
# ['python', 'model.py', '-n', 'run3', '-e', '30', '-b', '1', '-lr', '1e-08', '-ti', '300', '-ns', '1', '128', '256', '512', '1024']
# ['python', 'model.py', '-n', 'run4', '-e', '30', '-b', '1', '-lr', '1e-08', '-ti', '300', '-ns', '1', '16', '32', '64', '1024']
# ['python', 'model.py', '-n', 'run9', '-e', '30', '-b', '1', '-lr', '0.0001', '-ti', '300', '-ns', '1', '128', '256', '512', '1024']
# ['python', 'model.py', '-n', 'run10', '-e', '30', '-b', '1', '-lr', '0.0001', '-ti', '300', '-ns', '1', '16', '32', '64', '1024']

# addition of LrReduceOnPlateau
# REMEBER: quicks is in the main folder, slowers is in DDN2/DDN.. as otherwise the main could would've been overwritten with differences between them
# quicks (EqConstr).. (lr reduce on plateau for patience = 10)
# ['python', 'model.py', '-n', 'quick1', '-e', '50', '-b', '1', '-lr', '1e-05', '-ti', '50', '-ns', '1', '32', '32', '64', '1024', '-gpu', '0']
# ['python', 'model.py', '-n', 'quick2', '-e', '50', '-b', '1', '-lr', '0.0001', '-ti', '50', '-ns', '1', '32', '32', '64', '1024', '-gpu', '0']
# ['python', 'model.py', '-n', 'quick3', '-e', '50', '-b', '1', '-lr', '0.01', '-ti', '50', '-ns', '1', '32', '32', '64', '1024', '-gpu', '0']
# slowers (Abstract)... (lr reduce on plateau for patience = 3)
# ['python', 'model.py', '-n', 'slowerAbs1', '-e', '50', '-b', '2', '-lr', '0.01', '-ti', '10', '-ns', '1', '128', '256', '512', '1024', '-gpu', '1']
# ['python', 'model.py', '-n', 'slowerAbs2', '-e', '50', '-b', '2', '-lr', '0.01', '-ti', '300', '-ns', '1', '128', '256', '512', '1024', '-gpu', '1']
# ['python', 'model.py', '-n', 'slowerAbs3', '-e', '50', '-b', '1', '-lr', '0.01', '-ti', '5000', '-ns', '1', '128', '256', '512', '1024', '-gpu', '1']
