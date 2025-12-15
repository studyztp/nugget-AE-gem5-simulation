import sys
from pathlib import Path
import argparse

file_path = Path(__file__).resolve().parent.parent
print(file_path)
sys.path.append(str(file_path))

from gem5.simulate.simulator import Simulator
from gem5.simulate.exit_event import ExitEvent

from gem5.utils.requires import requires
from gem5.isas import ISA
from gem5.coherence_protocol import CoherenceProtocol

from workload.workload import get_specific_benchmark_workload, start_from_after_checkpoint

import m5

parser = argparse.ArgumentParser(description="Start Detailed Simulation")
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=["arm", "x86"])
parser.add_argument("--checkpoint-path", help="The path to the checkpoint to restore", required=True, type=str)
parser.add_argument("--checkpoint-output-dir", help="The directory to store the checkpoints", required=True, type=str)
parser.add_argument("--benchmark", help="The benchmark to run", required=True, type=str)
parser.add_argument("--size", help="The size of the benchmark", required=True, type=str)
parser.add_argument("--threads", help="The number of threads to run", required=True, type=int)
args = parser.parse_args()

checkpoint_path = Path(args.checkpoint_path)
checkpoint_output_dir = Path(args.checkpoint_output_dir)

arch = args.arch
benchmark = args.benchmark
size = args.size
threads = args.threads
workload = get_specific_benchmark_workload(arch, benchmark, size, threads)


checkpoint_output_dir = Path(checkpoint_output_dir/f"{arch}-{benchmark}-{size}-{threads}-cpt")

if args.arch == "arm":
    requires(isa_required=ISA.ARM, coherence_protocol_required=CoherenceProtocol.CHI)
    from boards.arm_board import *
    board = get_KVM_board()
elif args.arch == "x86":
    requires(isa_required=ISA.X86, coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL)
    start_from_after_checkpoint(workload, checkpoint_path)
    from boards.x86_board import *
    board = get_functional_board()

board.set_workload(workload)

def handel_workbegin():
    global checkpoint_output_dir
    print("Finish Initializing, start running the workload.")
    print("Taking a checkpoint.")
    m5.checkpoint(checkpoint_output_dir.as_posix())
    yield True

def ignore_exit_event():
    print("Ignoring exit first event.")
    yield False
    print("Ignoring exit second event.")
    yield False

simulator = Simulator(
    board=board,
    on_exit_event={
        ExitEvent.WORKBEGIN: handel_workbegin(),
        ExitEvent.EXIT: ignore_exit_event(),
})

simulator.run()

print("Simulation finished!")
