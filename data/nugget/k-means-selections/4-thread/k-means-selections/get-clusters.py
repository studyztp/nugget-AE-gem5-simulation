from pathlib import Path
from multiprocessing import Pool
import subprocess

root_path = Path(Path.cwd()).absolute()
current_dir = Path(__file__).parent
print(current_dir)

def run_this(run_ball):
    cmd = run_ball["cmd"]
    result = subprocess.run(" ".join(cmd), cwd=root_path, shell=True, capture_output=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(result.stderr.decode())
    else:
        print(f"Command succeeded: {cmd}")
        print(result.stdout.decode())
    return result.returncode

size = "A"
benchmarks = ["bt", "cg", "ep", "ft", "is", "lu", "mg", "sp"]
for i in range(len(benchmarks)):
    benchmarks[i] = f"{benchmarks[i]}_{size}"
num_ideal_nuggets = 30

workdir = Path(root_path/"experiments/4-threads-info/k-means-selections")
bb_info_dir = Path(root_path/"experiments/info/bb-info-output")
df_dir = Path(root_path/"experiments/4-threads-info/get-analysis-info")

if __name__ == "__main__":
    print("Running in main")

    all_runs = []

    for benchmark in benchmarks:
        benchmark_info_dir = Path(df_dir/benchmark)
        bb_info_path = Path(bb_info_dir/f"{benchmark}/basic-block-info.txt")
        df_path = Path(benchmark_info_dir/f"{benchmark}_df.csv")
        output_dir = Path(workdir/benchmark)
        cmd = ["python3", f"{current_dir}/clustering.py",
            "--bb_info_path", str(bb_info_path),
            "--df_path", str(df_path),
            "--num_ideal_nuggets", str(num_ideal_nuggets),
            "--output_dir", str(output_dir)
        ]
        run_ball = {
            "cmd": cmd,
        }
        all_runs.append(run_ball)

    with Pool(processes=20) as pool:
        pool.map(run_this, all_runs)

    print("done")

