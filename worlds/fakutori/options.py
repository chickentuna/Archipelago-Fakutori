from Options import Choice, DefaultOnToggle, Range, StartInventoryPool, PerGameCommonOptions
from dataclasses import dataclass

class VictoryCondition(Choice):
    display_name = "Victory Condition"
    option_all_blocks_discovered = 0
    option_all_block_challenges = 1
    option_spawn_quasar = 2
    default = 0

class ShopPrice(Choice):
    display_name = "Machine Unlock Price Reduction"
    option_full_price = 100
    option_50_percent_off = 50
    option_90_percent_off = 10
    default = 10

class StartWithDisassembler(DefaultOnToggle):
    display_name = "Start with Disassembler"

class StartWithBaseMachines(DefaultOnToggle):
    display_name = "Start with Conveyor, Wall, Combiner and Generators"

class ExtraShopChecks(Range):
    display_name = "Extra items in Machine unlock menu"
    range_start = 0
    range_end = 10
    default = 0
@dataclass
class FakutoriOptions(PerGameCommonOptions):
    start_inventory_from_pool: StartInventoryPool
    victory_condition: VictoryCondition
    shop_price: ShopPrice
    extra_shop_checks: ExtraShopChecks
    start_with_disassembler: StartWithDisassembler
    start_with_base_machines: StartWithBaseMachines

