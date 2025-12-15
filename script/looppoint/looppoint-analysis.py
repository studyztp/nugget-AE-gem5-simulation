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

from m5.objects import LooppointAnalysis, LooppointAnalysisManager, AddrRange

from workload.workload import get_specific_benchmark_workload, start_from_after_checkpoint

import json
import m5

parser = argparse.ArgumentParser(description="Start Detailed Simulation")
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=["arm", "x86"])
parser.add_argument("--checkpoint-path", help="The path to the checkpoint to restore", required=True, type=str)
parser.add_argument("--benchmark", help="The benchmark to run", required=True, type=str)
parser.add_argument("--size", help="The size of the benchmark", required=True, type=str)
parser.add_argument("--process-map-info-json-path", help="The path to the process map info json file", required=True, type=str)
parser.add_argument("--looppoint-analysis-output-dir", help="The path to the looppoint analysis output directory to store json file", required=True, type=str)
parser.add_argument("--threads", help="The number of threads to run the workload on", required=True, type=int)
args = parser.parse_args()

arch = args.arch
checkpoint_path = Path(args.checkpoint_path)
benchmark = args.benchmark
size = args.size
threads = args.threads
workload = get_specific_benchmark_workload(arch, benchmark, size, threads)
start_from_after_checkpoint(workload, checkpoint_path)
process_map_info_json_path = Path(args.process_map_info_json_path)
looppoint_analysis_output_dir = Path(args.looppoint_analysis_output_dir)

# this file will store the looppoint analysis results
output_file = Path(looppoint_analysis_output_dir/f"{arch}-{benchmark}-{size}-looppoint-analysis.json")

# initialize the output file
with open(output_file, "w") as f:
    json.dump({}, f)

# setup the looppoint analysis manager
manager = LooppointAnalysisManager()
# number of threads X 100_000_000 instructions is the proposed region length
# for the LoopPoint methodology
manager.region_length = 400_000_000
all_trackers = []

with open(process_map_info_json_path) as f:
    workload_process_map_info = json.load(f)

workload_info = workload_process_map_info[benchmark][arch]
source_address_range = workload_info["source_address_range"]
source_address_range = AddrRange(start=int(source_address_range[0],0), end=int(source_address_range[1],0))
restricted_address_ranges = workload_info["restricted_address_ranges"]
all_excluded_ranges = []
for restricted_address_range in restricted_address_ranges:
    all_excluded_ranges.append(AddrRange(start=int(restricted_address_range[0],0), end=int(restricted_address_range[1],0)))

if args.arch == "arm":
    requires(isa_required=ISA.ARM, coherence_protocol_required=CoherenceProtocol.CHI)
    from boards.arm_board import *
    board = get_functional_board()
elif args.arch == "x86":
    requires(isa_required=ISA.X86, coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL)
    from boards.x86_board import *
    board = get_functional_board()

for core in board.get_processor().get_cores():
    tracker = LooppointAnalysis()
    tracker.bb_valid_addr_range = AddrRange(0, 0)
    tracker.looppoint_analysis_manager = manager
    tracker.marker_valid_addr_range = source_address_range
    tracker.bb_excluded_addr_ranges = all_excluded_ranges
    core.core.probe_listener = tracker
    all_trackers.append(tracker)

board.set_workload(workload)

region_id = 0

def to_hex_map(the_map):
    new_map = {}
    for key, value in the_map.items():
        new_map[hex(key)] = value
    return new_map

def get_data():
    global region_id
    global manager
    global all_trackers
    global_bbv = manager.getGlobalBBV()
    global_bbv = to_hex_map(global_bbv)
    loop_counter = to_hex_map(manager.getBackwardBranchCounter())
    most_recent_loop = hex(manager.getMostRecentBackwardBranchPC())
    region_info = {
        "global_bbv" : global_bbv,
        "global_length" : manager.getGlobalInstCounter(),
        "global_loop_counter" : loop_counter,
        "most_recent_loop" : most_recent_loop,
        "most_recent_loop_count" : manager.getMostRecentBackwardBranchCount(),
        "bb_inst_map": to_hex_map(manager.getBBInstMap()),
        "locals" : []
    }
    for tracker in all_trackers:
        local_bbv = to_hex_map(tracker.getLocalBBV())
        region_info["locals"].append(local_bbv)
        tracker.clearLocalBBV()
    manager.clearGlobalBBV()
    manager.clearGlobalInstCounter()
    with open(output_file, "r") as f:
        data = json.load(f)
    data[region_id] = region_info
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)
    region_id += 1
    return region_id

def simpoint_handler():
    while True:
        current_region_id = get_data()
        print(f"Region {current_region_id-1} finished")
        yield False

def workend_handler():
    print("get to the end of the workload")
    current_region_id = get_data()
    print(f"Region {current_region_id-1} finished")
    yield True

simulator = Simulator(
    board=board,
    on_exit_event={
    ExitEvent.SIMPOINT_BEGIN:simpoint_handler(),
    ExitEvent.WORKEND:workend_handler(),
}
)

simulator.run()

print("Simulation finished!")
