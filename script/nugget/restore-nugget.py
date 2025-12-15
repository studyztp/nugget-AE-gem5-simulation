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

import m5

parser = argparse.ArgumentParser(description="Run the whole workload with detailed board")
parser.add_argument("--benchmark", help="The workload to run", required=True, type=str)
parser.add_argument("--marker-info-json-path", help="The json file that contains the marker information", required=True, type=str)
parser.add_argument("--rid", help="The region id to restore", required=True, type=int)
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=["arm", "x86"])
parser.add_argument("--size", help="The size of the benchmark", required=True, type=str)
parser.add_argument("--checkpoint-dir", help="The directory that stores all the checkpoints for looppoints", required=True, type=str)
parser.add_argument("--threads", help="The number of threads to run", required=True, type=int)
args = parser.parse_args()

size = args.size
benchmark = args.benchmark
marker_info_json_path = Path(args.marker_info_json_path)
checkpoint_dir = Path(args.checkpoint_dir)
arch = args.arch
threads = args.threads
rid = int(args.rid)

if arch == "arm":
    requires(isa_required=ISA.ARM, coherence_protocol_required=CoherenceProtocol.CHI)
    from boards.arm_board import *
    board = get_detailed_board()
elif arch == "x86":
    requires(isa_required=ISA.X86, coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL)
    from boards.x86_board import *
    board = get_detailed_board()

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

# current nugget marker needs to start counting from the end of the last marker
# therefore, we will track the first marker's pc count pair first
# then once we reach it, we will start tracking the second marker's pc count pair

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

max_tick = 1_000_000_000

# def dump_current_counters():
#     global tracker_manager
#     while True:
#         current_pc_count_pairs = convert_c_pc_count_pair_to_python(tracker_manager.getCurrentPcCountPair())
#         print(f"current tick: {m5.curTick()}")
#         print(f"current pc: {current_pc_count_pairs.get_pc()} with count {current_pc_count_pairs.get_count()}")
#         yield False

simulator = Simulator(
    board=board,
    on_exit_event={
        ExitEvent.WORKEND:handle_workend(),
        ExitEvent.SIMPOINT_BEGIN:reached_marker(),
        # ExitEvent.MAX_TICK: dump_current_counters(),
}
)

simulator.run()

print("Simulation finished!")
