from m5.objects.DRAMInterface import DDR4_2400_16x4

from gem5.isas import ISA
from gem5.components.memory.memory import ChanneledMemory
from boards.arm_board_components.components.boards import FullSystemArmBoard
from boards.arm_board_components.components.cmn import CoherentMeshNetwork
from boards.arm_board_components.components.processors import (
    VectorProcessor,
    ARM_SVE_Parameters,
)
from boards.arm_board_components.mods.noc_mods import get_bundle_from_version as noc_version
from boards.arm_board_components.mods.core_mods import get_bundle_from_version as core_version

from gem5.components.cachehierarchies.classic.no_cache import NoCache
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.boards.arm_board import ArmBoard
from m5.objects.ArmSystem import ArmDefaultRelease
from m5.objects.RealView import VExpress_GEM5_V1, VExpress_GEM5_Foundation

def get_detailed_board(vlen: int = 512):
    processor = VectorProcessor(ISA.ARM, 8, "novo")
    vector_parameters = ARM_SVE_Parameters(vlen=vlen, is_fullsystem=True)
    vector_parameters.apply_processor_change(processor)
    # 
    cache = CoherentMeshNetwork(cores_per_tile=2)
    memory = ChanneledMemory(DDR4_2400_16x4, 4, 128, size="8GiB")
    system = FullSystemArmBoard(
        clk_freq="3GHz",
        processor=processor,
        cache_hierarchy=cache,
        memory=memory,
        use_kvm=True,
    )
    vector_parameters.apply_system_change(system)

    system.add_modifier(noc_version(1))
    system.add_modifier(core_version(1))

    return system

def get_functional_board():
    processor = SimpleProcessor(
        cpu_type=CPUTypes.ATOMIC,
        isa=ISA.ARM,
        num_cores=8
    )
    cache = NoCache()
    memory = ChanneledMemory(DDR4_2400_16x4, 4, 128, size="8GiB")
    system = ArmBoard(
        clk_freq="3GHz",
        processor=processor,
        cache_hierarchy=cache,
        memory=memory,
        platform=VExpress_GEM5_V1(),
        release=ArmDefaultRelease().for_kvm()
    )
    return system

def get_KVM_board():
    processor = SimpleProcessor(
        cpu_type=CPUTypes.KVM,
        isa=ISA.ARM,
        num_cores=8
    )
    cache = NoCache()
    memory = ChanneledMemory(DDR4_2400_16x4, 4, 128, size="8GiB")
    system = ArmBoard(
        clk_freq="3GHz",
        processor=processor,
        cache_hierarchy=cache,
        memory=memory,
        platform=VExpress_GEM5_V1(),
        release=ArmDefaultRelease().for_kvm()
    )
    return system
