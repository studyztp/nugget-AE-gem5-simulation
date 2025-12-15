import sys
from pathlib import Path
import argparse
import json

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
file_path = Path(__file__).resolve().parent

from gem5.simulate.simulator import Simulator
from gem5.simulate.exit_event import ExitEvent

from gem5.utils.requires import requires
from gem5.isas import ISA
from gem5.coherence_protocol import CoherenceProtocol

from m5.objects import PcCountTracker, PcCountTrackerManager
from m5.params import PcCountPair

from workload.workload import get_nugget_workload, start_from_after_checkpoint

import shutil

import m5

parser = argparse.ArgumentParser(description="Run the whole workload with detailed board")
parser.add_argument("--benchmark", help="The benchmark to run", required=True, type=str)
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=["riscv", "arm", "x86"])
parser.add_argument("--output-dir", help="The directory to store the LoopPoint checkpoints", required=True, type=str)
parser.add_argument("--size", help="The size of the benchmark", required=True, type=str)
parser.add_argument("--rid", help="The region id to restore", required=True, type=int)
parser.add_argument("--after-boot-checkpoint-path", help="The path to the checkpoint to restore from", required=True, type=str)
parser.add_argument("--threads", help="The number of threads to run", required=True, type=int)
args = parser.parse_args()

size = args.size
benchmark = args.benchmark
output_dir = Path(args.output_dir)
arch = args.arch
rid = int(args.rid)
threads = args.threads
after_boot_checkpoint_path = Path(args.after_boot_checkpoint_path)

workload = get_nugget_workload(arch, benchmark, size, rid, threads)

if arch == "arm":
    requires(isa_required=ISA.ARM, coherence_protocol_required=CoherenceProtocol.CHI)
    from boards.arm_board import *
    if rid == 0:
        board = get_functional_board()
    else:
        board = get_KVM_board()
elif arch == "x86":
    requires(isa_required=ISA.X86, coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL)
    # start_from_after_checkpoint(workload=workload, checkpoint=after_boot_checkpoint_path)
    from boards.x86_board import *
    # board = get_functional_board()
    if rid == 0:
        board = get_functional_board()
    else:
        board = get_KVM_board()

def workbegin_handler():
    print("get to the beginning of the workload")
    print("Fall back to simulation")
    yield False
    print("warmup marker reaches")
    if rid == 0:
        print("for rid 0, we need to wait for the start marker")
        yield False
    print("checkpointing")    
    m5.checkpoint(Path(f"{args.output_dir}/{arch}-{benchmark}-{size}-{rid}-{threads}-cpt").as_posix())
    yield True

def ignore_exit_event():
    while True:
        print("ignore exit event")
        yield False

board.set_workload(workload)

simulator = Simulator(
    board=board,
    on_exit_event={
        ExitEvent.EXIT:ignore_exit_event(),
        ExitEvent.WORKBEGIN:workbegin_handler()
})

simulator.run()

print("Simulation finished!")
