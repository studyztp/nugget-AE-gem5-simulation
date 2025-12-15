# Nugget-AE gem5 Simulation

This guide summarizes the steps required to build gem5, prepare disk images, and launch the provided experiment suite for artifact evaluation.

## Prerequisites

- Linux host with build essentials and Python 3.
- Sufficient disk space for gem5 builds and disk images (tens of GBs).
- Network access for fetching any missing dependencies during disk image creation.

## 1) Build gem5 binaries

From the `gem5` root in this repository, build the two required fast binaries:

```bash
# X86 with MESI two-level coherence
scons build/X86_MESI_Two_Level/gem5.fast -j$(nproc)

# ARM (classic) build
scons build/ARM/gem5.fast -j$(nproc)
```

The resulting binaries will be at:

- `gem5/build/X86_MESI_Two_Level/gem5.fast`
- `gem5/build/ARM/gem5.fast`

Ensure both complete successfully before proceeding.

## 2) Build disk images

Create the ARM and x86 disk images using the helper scripts in `gem5-resources/src/nugget-diskimages`:

```bash
cd gem5-resources/src/nugget-diskimages

# Build ARM disk image
./build-arm.sh

# Build x86 disk image
./build-x86.sh
```

Each script will download base images and install workloads; allow time for package installations.

## 3) Run experiments

Two entry points are provided:

- `script/`: Individual experiment scripts (run one experiment at a time).
- `task-script/`: Orchestrators that spawn processes to run the full experiment matrix automatically.

**NOTE** Please run all the scripts at the `gem5-simulation` directory.

### Run a single experiment

Invoke the desired script under `scripts` directly, for example:

```bash
[gem5 binary] script/detailed-baseline.py [with all the required arguments]
```

Refer to inline script comments or `--help` flags (where available) for runtime options and output locations.
Because providing information for each experiment is messy, we recommend using the scripts in `task-script` to automatically manage and start experiments for you.

### Run the full suite

Use the corresponding wrapper under `task-script` to launch all experiments concurrently:

```bash
python3 task-script/take-after-boot-cpt.py [with all the required arguments]
```

These orchestrators will create sub-processes for the experiment set. Monitor console output for progress and logs for per-run details.

## Outputs and logs

Experiment outputs and checkpoints are written to the locations configured inside each task script. If you modify destinations, ensure to manage the different experiments.

## Troubleshooting tips

- It is likely to have issues in the building disk images part. Try to build outside of the Docker container if it doesn't work. Contact us if nothing works.
