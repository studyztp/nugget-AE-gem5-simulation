import subprocess
from multiprocessing import Pool
from pathlib import Path
import argparse 
import json

parser = argparse.ArgumentParser(description="Run looppoint analysis on all benchmarks")
parser.add_argument("--m5out-output-dir", help="The directory to store the m5out", required=True, type=str)
parser.add_argument("--gem5-binary-dir", help="The directory to store the gem5 binary", required=True, type=str)
parser.add_argument("--marker-info-json-path", help="The path to the marker info json file", required=True, type=str)
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=[ "arm", "x86"])
parser.add_argument("--nugget-checkpoint-output-dir", help="The path to the nugget checkpoint output directory to store checkpoints", required=True, type=str)
args = parser.parse_args()

m5out_output_dir = Path(args.m5out_output_dir)
gem5_binary_dir = Path(args.gem5_binary_dir)
marker_info_json_path = Path(args.marker_info_json_path)
arch = args.arch

nugget_checkpoint_output_dir = Path(args.nugget_checkpoint_output_dir)
nugget_checkpoint_output_dir = Path(nugget_checkpoint_output_dir/arch)

benchmarks = ["bt", "cg", "ep", "ft", "is", "lu", "mg", "sp"]
# benchmarks = ["cg", "ep", "ft", "is", "mg"]
# benchmarks = ["cg"]
# benchmarks = ["ep", "ft", "is", "mg"]
size = "A"
threads = 1

workdir = Path().cwd()

def run_this(run_ball):
    cmd = run_ball["cmd"]

    result = subprocess.run(cmd, check=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to run the script, return code: {result.returncode}")
    else:
        print("Successfully run the script.")

if arch == "arm":
    gem5_binary_path = Path(gem5_binary_dir/"ARM/gem5.fast")
else:
    gem5_binary_path = Path(gem5_binary_dir/"X86_MESI_Two_Level/gem5.fast")

if not gem5_binary_path.exists():
    raise FileNotFoundError(f"gem5 binary not found at {gem5_binary_path}")

m5out_output_dir = Path(m5out_output_dir/f"nugget/nugget-restore/{arch}")
m5out_output_dir.mkdir(parents=True, exist_ok=True)

all_run_balls = []

with open(marker_info_json_path, "r") as f:
    marker_data = json.load(f)

marker_data = marker_data[arch]

for binary, marker_info in marker_data.items():
    if threads == 1:
        binary_name_index = 3
        if not "m5_nugget_exe" in binary:
            continue
    else:
        #  ex: m5_nugget_4_threads_exe_bt_A_671
        binary_name_index = 5
        if not f"m5_nugget_{threads}_threads_exe" in binary:
            continue
    binary_name = binary.split("_")[binary_name_index]
    
    if binary_name not in benchmarks:
        continue
    rid = int(binary.split("_")[-1])


    bench_rid_m5out_output_dir = Path(m5out_output_dir/f"{arch}-{binary_name}-{size}-{rid}-{threads}-m5out")
    if Path(bench_rid_m5out_output_dir/"simout.txt").exists():
        if_finished = False
        with open(bench_rid_m5out_output_dir/"simout.txt", "r") as f:
            for line in f.readlines():
                if "end markers reached" in line:
                    if_finished = True
                    break
        if if_finished:
            print(f"Benchmark {binary_name} with RID {rid} already finished, skipping.")
            continue

    cmd = [
        gem5_binary_path.as_posix(),
        "-re",
        "--outdir", bench_rid_m5out_output_dir.as_posix(),
        f"{workdir.as_posix()}/script/nugget/restore-nugget.py",
        "--checkpoint-dir", nugget_checkpoint_output_dir.as_posix(),
        "--benchmark", binary_name,
        "--size", size,
        "--arch", arch,
        "--rid", str(rid),
        "--marker-info-json-path", marker_info_json_path.as_posix(),
        "--threads", str(threads),
    ]
    run_ball = {
        "cmd": cmd
    }
    all_run_balls.append(run_ball)

with Pool(8) as pool:
    pool.map(run_this, all_run_balls)

print("All benchmarks finished.")
