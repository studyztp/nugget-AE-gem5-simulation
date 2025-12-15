from gem5.resources.resource import WorkloadResource, obtain_resource,DiskImageResource
from pathlib import Path

file_path = Path(__file__).resolve().parent

disk_image_base_path = Path(file_path/"../gem5-resources/src/nugget-diskimages/")

base_readfile = """
#!/bin/bash

# First raise an exit to take a checkpoint
m5 checkpoint
# Then sleep for 1 second to make sure that we have a clean stop
sleep 1
# Finally, read the workload command from the file
if ! gem5-bridge readfile > /tmp/workload_cmd.sh; then
    echo "Failed to run gem5-bridge readfile, exiting!"
    rm -f /tmp/workload_cmd.sh
    if ! gem5-bridge exit; then
        # Useful for booting the disk image in (e.g.,) qemu for debugging
        echo "gem5-bridge exit failed, dropping to shell."
    fi
else
    echo "Running script from gem5-bridge stored in /tmp/workload_cmd.sh"
    chmod 755 /tmp/workload_cmd.sh
    /tmp/workload_cmd.sh
    echo "Done running script from gem5-bridge, exiting."
    rm -f /tmp/workload_cmd.sh
    gem5-bridge exit
fi
"""

def get_workload_resource(arch: str):
    if arch == "arm":
        disk = DiskImageResource(local_path=Path(disk_image_base_path/"arm-disk-image-24-04/arm-ubuntu"),root_partition="2")
        workload = WorkloadResource(
            function = "set_kernel_disk_workload",
            parameters = {
                "kernel" : obtain_resource(resource_id="arm64-linux-kernel-5.15.36"),
                "disk_image" : disk,
                "bootloader" : obtain_resource(resource_id="arm64-bootloader-foundation")
            }
        )
    elif arch == "x86":
        disk = DiskImageResource(local_path=Path(disk_image_base_path/"x86-disk-image-24-04/x86-ubuntu"))
        workload =  WorkloadResource(
            function = "set_kernel_disk_workload",
            parameters = {
                "kernel_args" : [
                    "earlyprintk=ttyS0",
                    "console=ttyS0",
                    "lpj=7999923",
                    "root=/dev/sda2"
                ],
                "kernel" : obtain_resource("x86-linux-kernel-5.4.0-105-generic"),
                "disk_image" : disk,
            }
        )
    else:
        raise ValueError(f"Unsupported architecture {arch}")
    return workload

def get_base_workload(arch: str):
    workload = get_workload_resource(arch)
    workload.set_parameter("readfile_contents", base_readfile)
    return workload

def get_specific_benchmark_workload(arch: str, benchmark: str, size: str, num_threads: int):
    workload = get_workload_resource(arch)
    if num_threads == 1:
        core_range = "0"
        binary_stem = "m5_naive_exe"
    else:
        core_range = f"0-{num_threads-1}"
        binary_stem = f"m5_naive_{num_threads}_threads_exe"
    workload.set_parameter("readfile_contents", 
f"""#!/bin/bash
export LD_LIBRARY_PATH=/usr/lib/llvm-18/lib
export OMP_NUM_THREADS={num_threads}
export OMP_SCHEDULE="static"
export OMP_DISPLAY_ENV=TRUE

# Disable ASLR
echo 12345 | sudo -S bash -c '
  echo 0 > /proc/sys/kernel/randomize_va_space
  echo -n "ASLR setting: "
  cat /proc/sys/kernel/randomize_va_space
'

echo "ASLR disabled, confirming..."

# Confirm it was changed
cat /proc/sys/kernel/randomize_va_space

echo "Running the benchmark with the following parameters:"
echo "Benchmark: {benchmark}"
echo "Size: {size}"
echo "Number of threads: {num_threads}"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "OMP_NUM_THREADS: $OMP_NUM_THREADS"
echo "Running the benchmark..."

# Run the benchmark
sudo -SE bash -c 'taskset -c {core_range} /home/gem5/nugget-protocol-NPB/cbuild/llvm-exec/{binary_stem}_{benchmark}_{size}/{binary_stem}_{benchmark}_{size}'

# Optional: give time to cool down or simulate pause
sleep 5
"""
    )
    return workload

def get_nugget_workload(arch: str, benchmark: str, size: str, rid:int, num_threads: int):
    workload = get_workload_resource(arch)
    if num_threads == 1:
        core_range = "0"
        binary_stem = f"m5_nugget_exe"
    else:
        core_range = f"0-{num_threads-1}"
        binary_stem = f"m5_nugget_{num_threads}_threads_exe"
    workload.set_parameter("readfile_contents", 
f"""#!/bin/bash
export LD_LIBRARY_PATH=/usr/lib/llvm-18/lib
export OMP_NUM_THREADS={num_threads}
export OMP_SCHEDULE="static"
export OMP_DISPLAY_ENV=TRUE

# Disable ASLR
echo 12345 | sudo -S bash -c '
  echo 0 > /proc/sys/kernel/randomize_va_space
  echo -n "ASLR setting: "
  cat /proc/sys/kernel/randomize_va_space
'

echo "ASLR disabled, confirming..."

# Confirm it was changed
cat /proc/sys/kernel/randomize_va_space

echo "Running the benchmark with the following parameters:"
echo "Benchmark: {benchmark}"
echo "Size: {size}"
echo "Number of threads: {num_threads}"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "OMP_NUM_THREADS: $OMP_NUM_THREADS"
echo "Running the benchmark..."

# Run the benchmark
sudo -SE bash -c 'taskset -c {core_range} /home/gem5/nugget-protocol-NPB/cbuild/llvm-exec/{binary_stem}_{benchmark}_{size}_{rid}/{binary_stem}_{benchmark}_{size}_{rid}'

# Optional: give time to cool down or simulate pause
sleep 5
"""
    )
    return workload

def start_from_after_checkpoint(workload: WorkloadResource, checkpoint: Path):
    workload.set_parameter("checkpoint", checkpoint)
    return workload

def get_specific_benchmark_mmap_workload(arch: str, benchmark: str, size: str, num_threads: int):
    workload = get_workload_resource(arch)
    workload.set_parameter("readfile_contents", 
f"""#!/bin/bash

# Set environment variables and run the executable in the background
export LD_LIBRARY_PATH=/usr/lib/llvm-18/lib
export OMP_NUM_THREADS={num_threads}

# Disable ASLR
echo 12345 | sudo -S bash -c '
  echo 0 > /proc/sys/kernel/randomize_va_space
  echo -n "ASLR setting: "
  cat /proc/sys/kernel/randomize_va_space
'

echo "ASLR disabled, confirming..."

# Confirm it was changed
cat /proc/sys/kernel/randomize_va_space

/home/gem5/nugget-protocol-NPB/cbuild/llvm-exec/m5_naive_exe_{benchmark}_{size}/m5_naive_exe_{benchmark}_{size} &

# Capture the process ID of the background process
PID=$!

sleep 0.06

# Stop the process
kill -SIGSTOP $PID

# Print the process ID
echo "PID is $PID"

# Use sudo to read the process's memory map and write it to a file
echo 12345 | sudo -S cat /proc/$PID/maps > process_map.txt

# Use m5 to write the file and then exit
m5 writefile process_map.txt
m5 exit
""")
    return workload


def get_nugget_mmap_workload(arch: str, benchmark: str, size: str, rid:int, num_threads: int):
    workload = get_workload_resource(arch)
    if num_threads == 1:
        binary_stem = f"m5_nugget_exe"
    else:
        binary_stem = f"m5_nugget_{num_threads}_threads_exe"
    workload.set_parameter("readfile_contents", 
f"""#!/bin/bash

# Set environment variables and run the executable in the background
export LD_LIBRARY_PATH=/usr/lib/llvm-18/lib
export OMP_NUM_THREADS={num_threads}

# Disable ASLR
echo 12345 | sudo -S bash -c '
  echo 0 > /proc/sys/kernel/randomize_va_space
  echo -n "ASLR setting: "
  cat /proc/sys/kernel/randomize_va_space
'

echo "ASLR disabled, confirming..."

# Confirm it was changed
cat /proc/sys/kernel/randomize_va_space

/home/gem5/nugget-protocol-NPB/cbuild/llvm-exec/{binary_stem}_{benchmark}_{size}_{rid}/{binary_stem}_{benchmark}_{size}_{rid} &

# Capture the process ID of the background process
PID=$!

sleep 0.06

# Stop the process
kill -SIGSTOP $PID

# Print the process ID
echo "PID is $PID"

# Use sudo to read the process's memory map and write it to a file
echo 12345 | sudo -S cat /proc/$PID/maps > process_map.txt

# Use m5 to write the file and then exit
m5 writefile process_map.txt
m5 exit
""")
    return workload

# lsms workloads

def get_lsms_workload_resource(arch: str):
    lsms_disk_image_base_path = Path(file_path/"../gem5-resources/src/lsms-diskimages/")
    if arch == "arm":
        disk = DiskImageResource(local_path=Path(lsms_disk_image_base_path/"arm-disk-image-24-04/arm-ubuntu"),root_partition="2")
        workload = WorkloadResource(
            function = "set_kernel_disk_workload",
            parameters = {
                "kernel" : obtain_resource(resource_id="arm64-linux-kernel-5.15.36"),
                "disk_image" : disk,
                "bootloader" : obtain_resource(resource_id="arm64-bootloader-foundation")
            }
        )
    elif arch == "x86":
        disk = DiskImageResource(local_path=Path(lsms_disk_image_base_path/"x86-disk-image-24-04/x86-ubuntu"))
        workload =  WorkloadResource(
            function = "set_kernel_disk_workload",
            parameters = {
                "kernel_args" : [
                    "earlyprintk=ttyS0",
                    "console=ttyS0",
                    "lpj=7999923",
                    "root=/dev/sda2"
                ],
                "kernel" : obtain_resource("x86-linux-kernel-5.4.0-105-generic"),
                "disk_image" : disk,
            }
        )
    else:
        raise ValueError(f"Unsupported architecture {arch}")
    return workload

def get_lsms_nugget_workload(arch: str, rid:int):
    workload = get_lsms_workload_resource(arch)
    workload.set_parameter("readfile_contents", 
f"""#!/bin/bash
export LD_LIBRARY_PATH=/usr/lib/llvm-19/lib
export OMP_NUM_THREADS=1
export OMP_SCHEDULE="static"
export OMP_DISPLAY_ENV=TRUE
export OMPI_ALLOW_RUN_AS_ROOT=1
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

# Disable ASLR
echo 12345 | sudo -S bash -c '
  echo 0 > /proc/sys/kernel/randomize_va_space
  echo -n "ASLR setting: "
  cat /proc/sys/kernel/randomize_va_space
'

echo "ASLR disabled, confirming..."

# Confirm it was changed
cat /proc/sys/kernel/randomize_va_space

echo "Running the benchmark with the following parameters:"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "OMP_NUM_THREADS: $OMP_NUM_THREADS"
echo "Running the benchmark..."

# Run the benchmark
echo "cd /home/gem5/nugget-protocol-lsms/experiments/input"

#sudo -SE bash -c 'mpirun -n 1 /home/gem5/nugget-protocol-lsms/cbuild/llvm-exec/lsms_m5_nuggets_exe_{rid}/lsms_m5_nuggets_exe_{rid} i_lsms'
cd /home/gem5/nugget-protocol-lsms/experiments/input && sudo -SE bash -c 'mpirun -n 1 /home/gem5/nugget-protocol-lsms/cbuild/llvm-exec/lsms_m5_nuggets_exe_{rid}/lsms_m5_nuggets_exe_{rid} i_lsms'

# Optional: give time to cool down or simulate pause
sleep 5
"""
    )
    return workload

def get_lsms_nugget_mmap_workload(arch: str, rid:int):
    workload = get_lsms_workload_resource(arch)
    workload.set_parameter("readfile_contents", 
f"""#!/bin/bash

# Set environment variables and run the executable in the background
export LD_LIBRARY_PATH=/usr/lib/llvm-18/lib
export OMP_NUM_THREADS=1

# Disable ASLR
echo 12345 | sudo -S bash -c '
  echo 0 > /proc/sys/kernel/randomize_va_space
  echo -n "ASLR setting: "
  cat /proc/sys/kernel/randomize_va_space
'

echo "ASLR disabled, confirming..."

# Confirm it was changed
cat /proc/sys/kernel/randomize_va_space

cd /home/gem5/nugget-protocol-lsms/experiments/input && mpirun -n 1 /home/gem5/nugget-protocol-lsms/cbuild/llvm-exec/lsms_m5_nuggets_exe_{rid}/lsms_m5_nuggets_exe_{rid} i_lsms &

MPIRUN_PID=$!

sleep 1  # Give time for program to start

# Find child processes of mpirun
PID=$(pgrep -P $MPIRUN_PID)

echo "Found real MPI program PID: $PID"

sleep 5  # Wait if needed

kill -SIGSTOP $PID

cat /proc/$PID/maps > process_map.txt

kill -SIGCONT $PID  # (optional) Resume if needed

m5 writefile process_map.txt
m5 exit

""")
    return workload
