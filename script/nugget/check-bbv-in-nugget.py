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
parser.add_argument("--rid", help="The region id to start from", required=True, type=int)
parser.add_argument("--marker-info-json-path", help="The json file that contains the marker information", required=True, type=str)
args = parser.parse_args()

arch = args.arch
checkpoint_path = Path(args.checkpoint_path)
marker_info_json_path = Path(args.marker_info_json_path)
benchmark = args.benchmark
size = args.size
threads = args.threads
rid = args.rid

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

source_address_range = AddrRange(start=0, end=0)
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

with open(args.marker_info_json_path, "r") as f:
    nugget_info = json.load(f)

nugget_info = nugget_info[arch]

if threads == 1:
    rid_markers = nugget_info[f"m5_nugget_exe_{benchmark}_{size}_{rid}"]
else:
    rid_markers = nugget_info[f"m5_nugget_{threads}_threads_exe_{benchmark}_{size}_{rid}"]

start_marker = rid_markers["start_marker_addr"]
start_count = rid_markers["start_count"]
end_marker = rid_markers["end_marker_addr"]
end_count = rid_markers["end_count"]

marker_map = {}

start_marker_pair = None
end_marker_pair = None

all_targets = []

if rid != 0:
    marker_map[PcCountPair(int(start_marker,0), int(start_count))] = "start marker"
    start_marker_pair = PcCountPair(int(start_marker,0), int(start_count))
    all_targets.append(start_marker_pair)
marker_map[PcCountPair(int(end_marker, 0), int(end_count))] = "end marker"
end_marker_pair = PcCountPair(int(end_marker,0), int(end_count))
all_targets.append(end_marker_pair)

tracker_manager = PcCountTrackerManager()
if start_marker_pair is not None:
    tracker_manager.targets = [start_marker_pair]
else:
    tracker_manager.targets = [end_marker_pair]

all_trackers = []

print(f"start marker: {start_marker_pair}")
print(f"end marker: {end_marker_pair}")
if start_marker_pair is not None:
    print(f"scheduled start marker: {start_marker_pair.get_pc()} with count {start_marker_pair.get_count()}")
else:
    print(f"scheduled end marker: {end_marker_pair.get_pc()} with count {end_marker_pair.get_count()}")

for core in board.get_processor().get_cores():
    tracker = PcCountTracker()
    if start_marker_pair is not None:
        tracker.targets = [start_marker_pair]
    else:
        tracker.targets = [end_marker_pair]
    tracker.ptmanager  = tracker_manager
    tracker.core = core.core
    core.core.probe_listener = tracker
    all_trackers.append(tracker)

def handle_workend():
    print(f"Encounter workend event, dump the stats. Current ticks: {m5.curTick()}.")
    m5.stats.dump()
    yield True

def convert_c_pc_count_pair_to_python(c_pc_count_pair):
    return PcCountPair(c_pc_count_pair.get_pc(), c_pc_count_pair.get_count())

def reached_marker():
    global tracker_manager
    global all_trackers
    global all_targets
    global start_marker_pair
    global end_marker_pair
    global marker_map
    while True:
        print("reached marker")
        current_pc_count_pairs = convert_c_pc_count_pair_to_python(tracker_manager.getCurrentPcCountPair())
        print(current_pc_count_pairs)
        marker_type = marker_map[current_pc_count_pairs]
        print(f"marker type: {marker_type}")
        all_targets.remove(current_pc_count_pairs)
        if len(all_targets) == 0:
            print("end markers reached")
            yield True
        else:
            print(f"remaining targets:")
            for target in all_targets:
                print(target)
                
            print("start markers reached")

            assert len(all_targets) == 1, f"we should only have one target left, but we have {len(all_targets)}"
            
            print("remove the end marker's pc count pair from the tracker manager")
            print(f"current pc: {current_pc_count_pairs.get_pc()} with count {current_pc_count_pairs.get_count()}")
            tracker_manager.removePcCountPair(int(current_pc_count_pairs.get_pc()), int(current_pc_count_pairs.get_count()))

            print(f"end marker: {end_marker_pair.get_pc()} with count {end_marker_pair.get_count()}")

            if int(current_pc_count_pairs.get_pc()) == int(end_marker_pair.get_pc()):
                # if the end marker's pc is the same as the start marker's pc
                print(f"{end_marker_pair.get_pc()} is the same as the start marker")
                print("resetting the counter for the pc")
                tracker_manager.resetCounters(int(end_marker_pair.get_pc()))
            else:
                print("remove the start marker's pc target from the trackers")
                print("add the end marker's pc target to the trackers")
                for tracker in all_trackers:
                    tracker.removeTarget(int(current_pc_count_pairs.get_pc()))
                    tracker.addTarget(int(end_marker_pair.get_pc()))

            print("add the end marker's pc count pair to the tracker manager")
            tracker_manager.addPcCountPair(int(end_marker_pair.get_pc()), int(end_marker_pair.get_count()))
            
            print("dump and reset stats")

            m5.stats.dump()
            m5.stats.reset()
            yield False

checkpoint_path = Path(checkpoint_dir/f"{arch}-{benchmark}-{size}-{rid}-{threads}-cpt")
workload = get_nugget_workload(arch, benchmark, size, rid, threads)
start_from_after_checkpoint(workload, checkpoint_path)

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
    ExitEvent.WORKBEGIN:reached_marker(),
}
)

simulator.run()

print("Simulation finished!")
