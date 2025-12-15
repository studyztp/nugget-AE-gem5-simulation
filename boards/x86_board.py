from m5.objects.DRAMInterface import DDR4_2400_16x4
from gem5.components.memory.memory import ChanneledMemory
from gem5.components.boards.x86_board import X86Board
from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy import MESITwoLevelCacheHierarchy
from boards.x86_board_components.sky_components.skylakeCPU import SkyLakeCPU
from gem5.components.memory.single_channel import SingleChannelDDR3_1600
from gem5.components.cachehierarchies.classic.no_cache import NoCache
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.components.processors.cpu_types import CPUTypes

def get_detailed_board():
    processor = SkyLakeCPU(num_cores=4)
    memory = ChanneledMemory(DDR4_2400_16x4, 2, 128, size="3GiB")
    cache = MESITwoLevelCacheHierarchy(
        l1i_size="64KiB",
        l1i_assoc="8",
        l1d_size="64KiB",
        l1d_assoc="8",
        l2_size="1MiB",
        l2_assoc="64",
        num_l2_banks=4
    )
    system = X86Board(
        cache_hierarchy=cache,
        clk_freq="4GHz",
        processor=processor,
        memory=memory,
    )
    return system

def get_functional_board():
    processor = SimpleProcessor(
        cpu_type=CPUTypes.ATOMIC,
        isa=ISA.X86,
        num_cores=4
    )
    cache = NoCache()
    memory = ChanneledMemory(DDR4_2400_16x4, 1, 128, size="3GiB")
    system = X86Board(
        clk_freq="4GHz",
        processor=processor,
        cache_hierarchy=cache,
        memory=memory,
    )
    return system

def get_KVM_board():
    processor = SimpleProcessor(
        cpu_type=CPUTypes.KVM,
        isa=ISA.X86,
        num_cores=4
    )
    cache = NoCache()
    memory = ChanneledMemory(DDR4_2400_16x4, 1, 128, size="3GiB")
    system = X86Board(
        clk_freq="4GHz",
        processor=processor,
        cache_hierarchy=cache,
        memory=memory,
    )
    return system
