from pathlib import Path
import pandas as pd
import argparse
import json
import sys

parser = argparse.ArgumentParser(description="Clustering")
parser.add_argument("--bb_info_path", type=str, help="Path to the bb info file")
parser.add_argument("--df_path", type=str, help="Path to the analysis dataframe")
parser.add_argument("--num_ideal_nuggets", type=int, help="Number of ideal nuggets")
parser.add_argument("--output_dir", type=str, help="Path to the output directory")

args = parser.parse_args()

bb_info_path = Path(args.bb_info_path)
df_path = Path(args.df_path)
num_ideal_nuggets = int(args.num_ideal_nuggets)
output_dir = Path(args.output_dir)

root_path = Path(Path.cwd()).absolute()
sys.path.append(root_path.as_posix())

from nugget_util.python_processing.analysis_functions import (
    get_all_bbv,
    form_bb_id_map,
    get_static_info,
    k_means_select_regions
)

num_ideal_nuggets = 30
num_projection = 100

def generate_k_means(nugget_info_path, analysis_df_path, num_ideal_nuggets, output_dir):
    global num_projection
    with open(analysis_df_path, "r") as f:
        df = pd.read_csv(f, header=0, dtype={'region': str, 'thread': int})

    bb_id_map = form_bb_id_map(df)

    all_bbv = get_all_bbv(df, bb_id_map)

    for index, row in enumerate(all_bbv):
        if sum(row) == 0:
            print(f"row {index} has all zeros")

    static_info = get_static_info(nugget_info_path)

    print(f"shape of all_bbv: {len(all_bbv)} {len(all_bbv[0])}")

    while len(all_bbv) <= num_ideal_nuggets * 4:
        num_ideal_nuggets /= 2
        num_ideal_nuggets = int(num_ideal_nuggets)

    if len(all_bbv[0]) <= num_projection:
        num_projection = len(all_bbv[0])
        num_projection = int(num_projection)

    num_projection = min(num_projection, len(all_bbv))

    kmeans_result = k_means_select_regions(
        num_ideal_nuggets,
        all_bbv,
        bb_id_map,
        static_info,
        num_projection
    )

    with open(Path(output_dir/"kmeans-result.json"), "w") as f:
        json.dump(kmeans_result, f, indent=4)

    rep_rid = kmeans_result["rep_rid"]

    with open(Path(output_dir/"selected-regions.txt"), "w") as f:
        for val in rep_rid.values():
            f.write(f"{val}\n")

    print("finished selecting regions")

if __name__ == "__main__":
    print("Running in main")

    print("Arguments:")
    print(f"bb_info_path: {bb_info_path}")
    print(f"df_path: {df_path}")
    print(f"num_ideal_nuggets: {num_ideal_nuggets}")
    print(f"output_dir: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    generate_k_means(
        bb_info_path,
        df_path,
        num_ideal_nuggets,
        output_dir
    )
    print("Done")

