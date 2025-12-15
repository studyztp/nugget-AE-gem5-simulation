from pathlib import Path
import pandas as pd
import json

workdir = Path("/home/studyztp/test_ground/experiments/nugget-micro/gem5-experiments")
nugget_restore_data_dir = Path(workdir/"m5outs/nugget/nugget-restore")
detailed_baseline_data_dir = Path(workdir/"m5outs/detailed-baseline")
k_means_clustering_data_dir = Path(workdir/"data/nugget/info/k-means-selections")

# isas = ["arm", "x86"]
isas = ["arm"]
benchmarks = ["cg", "ep","is", "mg", "ft"]

def get_detailed_stats(file):
    with open(file, 'r') as f:
        sim_seconds = 0.0
        sim_insts = 0.0
        for line in f:
            if "simSeconds" in line:
                sim_seconds = float(line.split()[1])
            if "simInsts" in line:
                sim_insts = float(line.split()[1])

    return sim_seconds, sim_insts

def get_restored_stats(file):
    with open(file, 'r') as f:
        sim_seconds = 0.0
        sim_insts = 0.0
        for line in f:
            if "simSeconds" in line:
                sim_seconds = float(line.split()[1])
            if "simInsts" in line:
                sim_insts = float(line.split()[1])
            if sim_seconds != 0.0 and sim_insts != 0.0:
                break
    return sim_seconds, sim_insts

df = pd.DataFrame(columns=["benchmark", "isa", "actual_sim_seconds", "actual_sim_insts", "predicted_sim_seconds", "prediction_error(%)","details", "num_samples", "total_num_intervals"])

for bench in benchmarks:
    for isa in isas:
        actual_sim_second, actual_sim_insts = get_detailed_stats(Path(detailed_baseline_data_dir/f"{isa}/{isa}-{bench}-A-m5out/stats.txt"))

        k_means_json_path = Path(k_means_clustering_data_dir/f"{bench}_A/kmeans-result.json")
        with open(k_means_json_path, 'r') as f:
            k_means_data = json.load(f)
        rep_rid = k_means_data["rep_rid"]
        clusters_weights = k_means_data["clusters_weights"]
        predicted_sim_second = 0.0
        
        details = {}

        total_num_intervals = 0
        num_samples = 0

        not_yet_done = False

        for cluster_id, rid in rep_rid.items():
            weight = clusters_weights[cluster_id]
            total_num_intervals += weight
            num_samples += 1
            if Path(nugget_restore_data_dir/f"{isa}/{isa}-{bench}-A-{rid}-m5out/stats.txt").exists():
                restore_sim_second, restore_sim_inst = get_detailed_stats(Path(nugget_restore_data_dir/f"{isa}/{isa}-{bench}-A-{rid}-m5out/stats.txt"))
            else:
                not_yet_done = True
                break
            details[cluster_id] = {
                "rid": rid,
                "weight": weight,
                "restore_sim_seconds": restore_sim_second,
                "restore_sim_insts": restore_sim_inst,
            }
            predicted_sim_second += weight * restore_sim_second
        if not_yet_done:
            continue
        prediction_error = 100*((predicted_sim_second - actual_sim_second) / actual_sim_second)

        df = pd.concat([df,
                        pd.DataFrame({
                            "benchmark": [bench],
                            "isa": [isa],
                            "actual_sim_seconds": [actual_sim_second],
                            "actual_sim_insts": [actual_sim_insts],
                            "predicted_sim_seconds": [predicted_sim_second],
                            "prediction_error(%)": [prediction_error],
                            "details": [details],
                            "num_samples": [num_samples],
                            "total_num_intervals": [total_num_intervals]
                        })], ignore_index=True)
        
df.to_csv("looppoint-evaluation.csv", index=False)
