import sys
from pathlib import Path
import argparse

file_path = Path(__file__).resolve().parent.parent.parent
print(file_path)
sys.path.append(str(file_path))

from gem5.simulate.simulator import Simulator
from gem5.simulate.exit_event import ExitEvent

from gem5.utils.requires import requires
from gem5.isas import ISA
from gem5.coherence_protocol import CoherenceProtocol

from workload.workload import get_nugget_mmap_workload, start_from_after_checkpoint

import m5

parser = argparse.ArgumentParser(description="Start Detailed Simulation")
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=["arm", "x86"])
parser.add_argument("--benchmark", help="The benchmark to run", required=True, type=str)
parser.add_argument("--size", help="The size of the benchmark", required=True, type=str)
parser.add_argument("--rid", help="The ride to run the workload on", required=True, type=str)
parser.add_argument("--after-boot-checkpoint-path", help="The path to the checkpoint to restore from", required=True, type=str)
parser.add_argument("--threads", help="The number of threads to run", required=True, type=int)
args = parser.parse_args()

arch = args.arch
rid = int(args.rid)
benchmark = args.benchmark
after_boot_checkpoint_path = Path(args.after_boot_checkpoint_path)
threads = args.threads
size = args.size
workload = get_nugget_mmap_workload(arch, benchmark, size, rid, threads)
start_from_after_checkpoint(workload=workload, checkpoint=after_boot_checkpoint_path)

max_tick = 1000_000_000_000

if args.arch == "arm":
    requires(isa_required=ISA.ARM, coherence_protocol_required=CoherenceProtocol.CHI)
    from boards.arm_board import *
    board = get_KVM_board()
elif args.arch == "x86":
    requires(isa_required=ISA.X86, coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL)
    from boards.x86_board import *
    board = get_functional_board()

board.set_workload(workload)

simulator = Simulator(
    board=board,
)

simulator.run()

print("Simulation finished!")
