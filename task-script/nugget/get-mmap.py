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
parser.add_argument("--after-boot-checkpoint-path", help="The path to the checkpoint to restore from", required=True, type=str)
args = parser.parse_args()

m5out_output_dir = Path(args.m5out_output_dir)
gem5_binary_dir = Path(args.gem5_binary_dir)
marker_info_json_path = Path(args.marker_info_json_path)
after_boot_checkpoint_path = Path(args.after_boot_checkpoint_path)
after_boot_checkpoint_path = Path(after_boot_checkpoint_path/f"{args.arch}-after-boot-cpt")
arch = args.arch

# benchmarks = ["bt", "cg", "ep", "ft", "is", "lu", "mg", "sp"]
benchmarks = ["cg", "ep", "ft", "is", "mg"]
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

m5out_output_dir = Path(m5out_output_dir/f"nugget/get-mmap/{arch}")
m5out_output_dir.mkdir(parents=True, exist_ok=True)

all_run_balls = []

with open(marker_info_json_path, "r") as f:
    marker_data = json.load(f)

marker_data = marker_data[arch]

for binary, marker_info in marker_data.items():
    binary_name = binary.split("_")[3]
    if binary_name not in benchmarks:
        continue
    rid = int(binary.split("_")[-1])
    bench_rid_m5out_output_dir = Path(m5out_output_dir/f"{arch}-{binary_name}-{size}-{rid}-{threads}-m5out")
    cmd = [
        gem5_binary_path.as_posix(),
        "-re",
        "--outdir", bench_rid_m5out_output_dir.as_posix(),
        f"{workdir.as_posix()}/script/nugget/get-mmap.py",
        "--benchmark", binary_name,
        "--size", size,
        "--arch", arch,
        "--rid", str(rid),
        "--after-boot-checkpoint-path", after_boot_checkpoint_path.as_posix(),
        "--threads", str(threads),
    ]
    run_ball = {
        "cmd": cmd
    }
    all_run_balls.append(run_ball)

with Pool(1) as pool:
    pool.map(run_this, all_run_balls)

print("All benchmarks finished.")
