import subprocess
from multiprocessing import Pool
from pathlib import Path
import argparse 

parser = argparse.ArgumentParser(description="Run looppoint analysis on all benchmarks")
parser.add_argument("--checkpoint-dir", help="The directory to store the checkpoints", required=True, type=str)
parser.add_argument("--m5out-output-dir", help="The directory to store the m5out", required=True, type=str)
parser.add_argument("--gem5-binary-dir", help="The directory to store the gem5 binary", required=True, type=str)
parser.add_argument("--process-map-info-json-path", help="The path to the process map info json file", required=True, type=str)
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=[ "arm", "x86"])
parser.add_argument("--looppoint-analysis-output-dir", help="The path to the looppoint analysis output directory to store json file", required=True, type=str)
args = parser.parse_args()

checkpoint_dir = Path(args.checkpoint_dir)
m5out_output_dir = Path(args.m5out_output_dir)
gem5_binary_dir = Path(args.gem5_binary_dir)
process_map_info_json_path = Path(args.process_map_info_json_path)
looppoint_analysis_output_dir = Path(args.looppoint_analysis_output_dir)
arch = args.arch

if not process_map_info_json_path.exists():
    raise FileNotFoundError(f"process map info json file not found at {process_map_info_json_path}")
looppoint_analysis_output_dir.mkdir(parents=True, exist_ok=True)

benchmarks = ["bt", "cg", "ep", "ft", "is", "lu", "mg", "sp"]
size = "A"
threads = 4

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

m5out_output_dir = Path(m5out_output_dir/f"looppoint/looppoint-analysis/{arch}")
m5out_output_dir.mkdir(parents=True, exist_ok=True)

all_run_balls = []

for bench in benchmarks:
    bench_m5out_output_dir = Path(m5out_output_dir/f"{arch}-{bench}-{size}-{threads}-m5out")
    bench_checkpoint_path = Path(checkpoint_dir/f"{arch}-{bench}-{size}-{threads}-cpt")
    if not bench_checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at {bench_checkpoint_path}")
    cmd = [
        gem5_binary_path.as_posix(),
        "-re",
        "--outdir", bench_m5out_output_dir.as_posix(),
        f"{workdir.as_posix()}/script/looppoint/looppoint-analysis.py",
        "--checkpoint-path", bench_checkpoint_path.as_posix(),
        "--looppoint-analysis-output-dir", looppoint_analysis_output_dir.as_posix(),
        "--process-map-info-json-path", process_map_info_json_path.as_posix(),
        "--benchmark", bench,
        "--size", size,
        "--arch", arch,
        "--threads", str(threads),
    ]
    run_ball = {
        "cmd": cmd
    }
    all_run_balls.append(run_ball)

with Pool() as pool:
    pool.map(run_this, all_run_balls)

print("All benchmarks finished.")
