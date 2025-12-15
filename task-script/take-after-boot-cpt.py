import subprocess
from pathlib import Path
import argparse 

parser = argparse.ArgumentParser(description="Take checkpoints after booting the system")
parser.add_argument("--checkpoint-output-dir", help="The directory to store the checkpoints", required=True, type=str)
parser.add_argument("--m5out-output-dir", help="The directory to store the m5out", required=True, type=str)
parser.add_argument("--gem5-binary-dir", help="The directory to store the gem5 binary", required=True, type=str)
parser.add_argument("--arch", help="The architecture to run the workloads on", required=True, type=str, choices=[ "arm", "x86"])
args = parser.parse_args()

checkpoint_output_dir = Path(args.checkpoint_output_dir)
m5out_output_dir = Path(args.m5out_output_dir)
gem5_binary_dir = Path(args.gem5_binary_dir)
arch = args.arch

workdir = Path().cwd()

if arch == "arm":
    gem5_binary_path = Path(gem5_binary_dir/"ARM/gem5.fast")
else:
    gem5_binary_path = Path(gem5_binary_dir/"X86_MESI_Two_Level/gem5.fast")

if not gem5_binary_path.exists():
    raise FileNotFoundError(f"gem5 binary not found at {gem5_binary_path}")

m5out_output_dir = Path(m5out_output_dir/f"after-boot-m5out/{arch}-m5out/")
checkpoint_output_dir = Path(checkpoint_output_dir/f"after-boot-cpt/")
m5out_output_dir.mkdir(parents=True, exist_ok=True)
checkpoint_output_dir.mkdir(parents=True, exist_ok=True)

cmd = [
    gem5_binary_path.as_posix(),
    "-re",
    "--outdir", m5out_output_dir.as_posix(),
    f"{workdir.as_posix()}/script/take-after-boot-cpt.py",
    "--checkpoint-output-dir", checkpoint_output_dir.as_posix(),
    "--arch", arch
]

result = subprocess.run(cmd, check=True)

if result.returncode != 0:
    raise RuntimeError(f"Failed to run the script, return code: {result.returncode}")
else:
    print("Successfully run the script.")

