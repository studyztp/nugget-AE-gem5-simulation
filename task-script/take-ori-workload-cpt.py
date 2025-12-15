import subprocess
from multiprocessing import Pool
from pathlib import Path
import argparse 

parser = argparse.ArgumentParser(description="Take checkpoints after booting the system")
parser.add_argument("--checkpoint-dir", help="The directory to store the checkpoints", required=False, type=str)
parser.add_argument("--m5out-output-dir", help="The directory to store the m5out", required=True, type=str)
parser.add_argument("--gem5-binary-dir", help="The directory to store the gem5 binary", required=True, type=str)
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=[ "arm", "x86"])
parser.add_argument("--checkpoint-output-dir", help="The directory to store the checkpoints", required=True, type=str)
parser.add_argument("--benchmark", "-b", help="The benchmark to run. Input as a list of benchmarks, for example, -b='bt cg ep'. (default: bt, cg, ep, ft, is, lu, mg, sp)", default=["bt", "cg", "ep", "ft", "is", "lu", "mg", "sp"], action="append")
parser.add_argument("--threads", "-t", help="The number of threads to run the workloads with", required=False, type=int, default=4)
args = parser.parse_args()

checkpoint_dir = Path(args.checkpoint_dir)
checkpoint_output_dir = Path(args.checkpoint_output_dir)
chechpoint_output_dir = Path(checkpoint_output_dir/f"ori-workload-cpt")
chechpoint_output_dir.mkdir(parents=True, exist_ok=True)
m5out_output_dir = Path(args.m5out_output_dir)
gem5_binary_dir = Path(args.gem5_binary_dir)
arch = args.arch

benchmarks = args.benchmark
size = "A"
threads = args.threads

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
    checkpoint_path = Path(checkpoint_dir/f"x86-after-boot-cpt")

if not gem5_binary_path.exists():
    raise FileNotFoundError(f"gem5 binary not found at {gem5_binary_path}")
if not checkpoint_path.exists():
    raise FileNotFoundError(f"checkpoint path not found at {checkpoint_path}")

m5out_output_dir = Path(m5out_output_dir/f"ori-workload-cpt-m5out/{arch}")
m5out_output_dir.mkdir(parents=True, exist_ok=True)

all_run_balls = []

for bench in benchmarks:
    bench_m5out_output_dir = Path(m5out_output_dir/f"{arch}-{bench}-{size}-m5out")
    if Path(checkpoint_output_dir/f"{arch}-{bench}-{size}-{threads}-cpt").exists():
        print(f"Checkpoint for {arch} {bench} already exists, skipping...")
        continue
    cmd = [
        gem5_binary_path.as_posix(),
        "-re",
        "--outdir", bench_m5out_output_dir.as_posix(),
        f"{workdir.as_posix()}/script/take-ori-workload-cpt.py",
        "--checkpoint-path", checkpoint_path.as_posix(),
        "--checkpoint-output-dir", chechpoint_output_dir.as_posix(),
        "--benchmark", bench,
        "--size", size,
        "--arch", arch,
        "--threads", str(threads),
    ]
    run_ball = {
        "cmd": cmd
    }
    all_run_balls.append(run_ball)

# if arch == "arm":
#     with Pool(1) as pool:
#         pool.map(run_this, all_run_balls)
# else:
#     with Pool(1) as pool:
#         pool.map(run_this, all_run_balls)
if arch == "arm":
    with open(Path(workdir/f"task-script/{arch}-take-ori-workload-cpt.sh"), "w") as f:
        for run_ball in all_run_balls:
            cmd = run_ball["cmd"]
            f.write(" ".join(cmd) + "\n")
else:
    with Pool(10) as pool:
        pool.map(run_this, all_run_balls)

print("bash script created.")
