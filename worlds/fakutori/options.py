from Options import Choice, DeathLink, DefaultOnToggle, Range, StartInventoryPool, PerGameCommonOptions
from dataclasses import dataclass

# TODO: reduce prices option

@dataclass
class FakutoriOptions(PerGameCommonOptions):
    death_link: DeathLink
    start_inventory_from_pool: StartInventoryPool