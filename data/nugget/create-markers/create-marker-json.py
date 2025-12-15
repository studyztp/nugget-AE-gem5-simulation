from pathlib import Path
import json
import pandas as pd

benchmarks = ["bt_A", "cg_A", "ep_A", "ft_A", "is_A", "lu_A", "mg_A", "sp_A"]

marker_dir = Path().__file__.parent
marker_addr_dir = Path(marker_dir/"marker_addr")

isas = ["arm", "x86"]
# isas = ["arm"]

addr_base = {
    "arm": "0",
    "x86": "0",
}

converted_markers = {
    "arm": {

    },
    "x86": {

    }
}

for isa in isas:
    marker_addr_json_path = Path(marker_addr_dir/f"{isa}/addr_map.json")
    with open(marker_addr_json_path, "r") as f:
        marker_addr = json.load(f)

    for benchmark in benchmarks:
        single_threaded_marker_csv = Path(marker_dir/f"1-thread/0.98/{benchmark}/markers.csv")
        single_threaded_marker_df = pd.read_csv(single_threaded_marker_csv)
        four_threaded_marker_csv = Path(marker_dir/f"4-thread/0.98/{benchmark}/markers.csv")
        four_threaded_marker_df = pd.read_csv(four_threaded_marker_csv)

        for binary_name, addrs in marker_addr.items():
            if benchmark not in binary_name:
                continue
            if "4_threads" in binary_name:
                marker_df = four_threaded_marker_df
            else:
                marker_df = single_threaded_marker_df
                
            rid = int(binary_name.split("_")[-1])

            start_count = marker_df[marker_df["region"]==rid]["start_count"].values[0]
            start_count = int(start_count)
            
            end_count = marker_df[marker_df["region"]==rid]["end_count"].values[0]
            end_count = int(end_count)
            
            start_marker_addr = addrs["start_marker_addr"]
            end_marker_addr = addrs["end_marker_addr"]

            if start_marker_addr is None:
                start_marker_addr = end_marker_addr

            start_marker_addr = int(start_marker_addr, 16) + int(addr_base[isa], 16)
            end_marker_addr = int(end_marker_addr, 16) + int(addr_base[isa], 16)

            start_marker_addr = hex(start_marker_addr)
            end_marker_addr = hex(end_marker_addr)

            converted_markers[isa][binary_name] = {
                "start_marker_addr": start_marker_addr,
                "end_marker_addr": end_marker_addr,
                "start_count": start_count,
                "end_count": end_count
            }

with open(marker_dir/"converted_markers.json", "w") as f:
    json.dump(converted_markers, f, indent=4)
print("Converted markers saved to converted_markers.json")

