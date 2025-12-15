import subprocess
from multiprocessing import Pool
from pathlib import Path
import argparse 

parser = argparse.ArgumentParser(description="Take checkpoints after booting the system")
# parser.add_argument("--checkpoint-dir", help="The directory to store the checkpoints", required=True, type=str)
parser.add_argument("--m5out-output-dir", help="The directory to store the m5out", required=True, type=str)
parser.add_argument("--gem5-binary-dir", help="The directory to store the gem5 binary", required=True, type=str)
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=[ "arm", "x86"])
args = parser.parse_args()

# checkpoint_dir = Path(args.checkpoint_dir)
m5out_output_dir = Path(args.m5out_output_dir)
gem5_binary_dir = Path(args.gem5_binary_dir)
arch = args.arch

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
    # checkpoint_path = Path(checkpoint_dir/f"arm-after-boot-cpt")
else:
    gem5_binary_path = Path(gem5_binary_dir/"X86_MESI_Two_Level/gem5.fast")
    # checkpoint_path = Path(checkpoint_dir/f"x86-after-boot-cpt")

if not gem5_binary_path.exists():
    raise FileNotFoundError(f"gem5 binary not found at {gem5_binary_path}")
# if not checkpoint_path.exists():
    # raise FileNotFoundError(f"checkpoint path not found at {checkpoint_path}")

m5out_output_dir = Path(m5out_output_dir/f"looppoint/get-mmap/{arch}")
m5out_output_dir.mkdir(parents=True, exist_ok=True)

all_run_balls = []

for bench in benchmarks:
    bench_m5out_output_dir = Path(m5out_output_dir/f"{arch}-{bench}-{size}-{threads}-m5out")
    cmd = [
        gem5_binary_path.as_posix(),
        "-re",
        "--outdir", bench_m5out_output_dir.as_posix(),
        f"{workdir.as_posix()}/script/looppoint/get-mmap.py",
        # "--checkpoint-path", checkpoint_path.as_posix(),
        "--benchmark", bench,
        "--size", size,
        "--arch", arch,
        "--threads", str(threads),
    ]
    run_ball = {
        "cmd": cmd
    }
    all_run_balls.append(run_ball)

with Pool(1) as pool:
    pool.map(run_this, all_run_balls)

print("All benchmarks finished.")
