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

from workload.workload import get_base_workload

import m5

parser = argparse.ArgumentParser(description="Take checkpoints after booting the system")
parser.add_argument("--checkpoint-output-dir", help="The directory to store the checkpoints", required=True, type=str)
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=["riscv", "arm", "x86"])
args = parser.parse_args()

arch = args.arch
checkpoint_output_dir = Path(args.checkpoint_output_dir)
workload = get_base_workload(arch)

if arch == "arm":
    requires(isa_required=ISA.ARM, coherence_protocol_required=CoherenceProtocol.CHI)
    from boards.arm_board import *
    checkpoint_output_dir = Path(checkpoint_output_dir/f"arm-after-boot-cpt")
    board = get_KVM_board()
elif arch == "x86":
    requires(isa_required=ISA.X86, coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL)
    from boards.x86_board import *
    checkpoint_output_dir = Path(checkpoint_output_dir/f"x86-after-boot-cpt")
    board = get_functional_board()

def handel_exit(cpt_output_dir):
    print("Encounter Kernel gem5-bridge exit event, ignore it.")
    yield False
    print("Encounter after-boot.sh exit event, take a checkpoint.")
    print(f"Current tick: {m5.curTick()}")
    m5.checkpoint(cpt_output_dir)
    yield True

board.set_workload(workload)

simulator = Simulator(
    board=board,
    on_exit_event={
        ExitEvent.EXIT: handel_exit(checkpoint_output_dir.as_posix())
})

simulator.run()

print("Simulation finished!")