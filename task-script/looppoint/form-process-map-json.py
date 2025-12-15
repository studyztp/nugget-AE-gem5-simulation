from pathlib import Path
import json
import argparse

parser = argparse.ArgumentParser(description="Extract LoopPoint needed information from the m5out")
parser.add_argument("--m5out-base-dir", help="The path to the m5out directory", required=True, type=str)
parser.add_argument("--output-dir", help="The directory to store the extracted information", required=True, type=str)
args = parser.parse_args()

m5_out_base_dir = Path(args.m5out_base_dir)
output_dir = Path(args.output_dir)

def parse_all_addresses(file_path):
    all_objects = {}
    with open(file_path) as f:
        data = f.readlines()
        for line in data:
            line_data = line.split()
            if len(line_data) < 6:
                continue
            # print(line_data)
            start_addr = line_data[0].split("-")[0]
            end_addr = line_data[0].split("-")[1]
            permission = line_data[1]
            object = line_data[5]
            object_name = object.split("/")[-1]
            if object_name not in all_objects:
                all_objects[object_name] = {}
            if permission not in all_objects[object_name]:
                all_objects[object_name][permission] = []
            all_objects[object_name][permission].append((start_addr, end_addr))
    return all_objects

omp_related_libraries_keywords = [
    "omp",
    "libarcher",
    "pthread"
]

all_info = {}

for isa_dir in m5_out_base_dir.iterdir():
    isa = isa_dir.name
    for m5_out_dir in isa_dir.iterdir():
        dir_name = m5_out_dir.name
        benchmark = dir_name.split("-")[1]
        size = dir_name.split("-")[2]
        if not Path(m5_out_dir/"process_map.txt").exists():
            continue
        address_info = parse_all_addresses(m5_out_dir/"process_map.txt")
        target_key = None
        for key in address_info.keys():
            if f"m5_naive_exe_{benchmark}_{size}" in key:
                target_key = key
                break
        exec_info = address_info[target_key]["r-xp"]
        start_source_addr = f"0x{exec_info[0][0]}"
        end_source_addr = "0x0"
        for addr in exec_info:
            if int(addr[0],16) < int(start_source_addr,0):
                start_source_addr = f"0x{addr[0]}"
            if int(addr[1],16) > int(end_source_addr,0):
                end_source_addr = f"0x{addr[1]}"
        source_address_range = (start_source_addr, end_source_addr)
        target_key = None
        restricted_address_ranges = []
        for key in address_info.keys():
            for keyword in omp_related_libraries_keywords:
                if keyword in key:
                    # print(key)
                    for permission, address_ranges in address_info[key].items():
                        for address_range in address_ranges:
                            restricted_address_ranges.append((f"0x{address_range[0]}", f"0x{address_range[1]}"))
                    # print(restricted_address_ranges)
        if benchmark not in all_info:
            all_info[benchmark] = {}
        all_info[benchmark][isa] = {
            "source_address_range" : source_address_range,
            "restricted_address_ranges" : restricted_address_ranges
        }
        print(f"Finish processing {benchmark}")

with open(output_dir/f"class_{size}_process_map_info.json", "w") as f:
    json.dump(all_info, f, indent=4)

print("Finish processing all benchmarks")

