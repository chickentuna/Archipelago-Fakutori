from Options import Choice, Toggle, DefaultOnToggle, Range, StartInventoryPool, PerGameCommonOptions
from dataclasses import dataclass

class VictoryCondition(Choice):
    """Sets the goal of your world.

    - **All Elements Discovered:** Create each element block once, filling the compendium.
    - **All Block Challenges:** Complete the block challenge of every challenge-bearing block.
      Forces Include Block Challenges on.
    - **Spawn Quasar:** Complete the demo: spawn a Quasar block."""
    display_name = "Victory Condition"
    option_all_elements_discovered = 0
    option_all_block_challenges = 1
    option_spawn_quasar = 2
    default = 2

class IncludeBlockChallenges(Toggle):
    """Adds each block's challenge (e.g. "make 10 copies", "burn 5 blocks") as an extra location
    check, on top of discovering the block. Automatically enabled when the goal is All Block
    Challenges."""
    display_name = "Include Block Challenges"

class ShopPrice(Choice):
    """Reduces the price of machine unlocks in the shop. Recommended if you do not start with disassembler."""
    display_name = "Machine Unlock Price Reduction"
    option_full_price = 100
    option_50_percent_off = 50
    option_90_percent_off = 10
    default = 50

class StartWithDisassembler(DefaultOnToggle):
    """Disassembler is unlocked and its shop location is removed."""
    display_name = "Start with Disassembler"

class StartWithBaseMachines(DefaultOnToggle):
    """Base machines are shuffled into the item pool."""
    display_name = "Start with Conveyor, Wall, Combiner and Generators"

class ExtraShopChecks(Range):
    """Adds extra machine unlocks. They will cost 2000 gold and have any item from the pool."""
    display_name = "Extra items in Machine unlock menu"
    range_start = 0
    range_end = 10
    default = 4
@dataclass
class FakutoriOptions(PerGameCommonOptions):
    start_inventory_from_pool: StartInventoryPool
    victory_condition: VictoryCondition
    include_block_challenges: IncludeBlockChallenges
    shop_price: ShopPrice
    extra_shop_checks: ExtraShopChecks
    start_with_disassembler: StartWithDisassembler
    start_with_base_machines: StartWithBaseMachines

