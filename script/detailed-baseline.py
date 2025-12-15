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
parser.add_argument("--benchmark", help="The benchmark to run", required=True, type=str)
parser.add_argument("--size", help="The size of the benchmark", required=True, type=str)
parser.add_argument("--threads", help="The number of threads to run", required=True, type=int)
args = parser.parse_args()

arch = args.arch
checkpoint_path = Path(args.checkpoint_path)
benchmark = args.benchmark
size = args.size
threads = args.threads
workload = get_specific_benchmark_workload(arch, benchmark, size, threads)
start_from_after_checkpoint(workload, checkpoint_path)

max_tick = 500_000_000_000

if args.arch == "arm":
    requires(isa_required=ISA.ARM, coherence_protocol_required=CoherenceProtocol.CHI)
    from boards.arm_board import *
    board = get_detailed_board()
elif args.arch == "x86":
    requires(isa_required=ISA.X86, coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL)
    from boards.x86_board import *
    board = get_detailed_board()

board.set_workload(workload)

def handel_workend():
    print("Workload finished, dumping stats.")
    m5.stats.dump()
    # yield True
    yield False

def handle_max_tick():
    while True:
        print(f"Encounter max tick event, dump the stats. Current ticks: {m5.curTick()}.")
        m5.stats.dump()
        yield False

simulator = Simulator(
    board=board,
    on_exit_event={
        ExitEvent.WORKEND: handel_workend(),
        ExitEvent.MAX_TICK:handle_max_tick()
})

simulator.run()

print("Simulation finished!")
