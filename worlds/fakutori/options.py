from Options import Choice, DeathLink, DefaultOnToggle, Range, StartInventoryPool, PerGameCommonOptions
from dataclasses import dataclass

class ShopPrice(Choice):
    """
    Reduce the costs of Archipelago items in shops.
    """
    display_name = "Shop Price Reduction"
    option_full_price = 100
    option_25_percent_off = 75
    option_50_percent_off = 50
    option_75_percent_off = 25
    default = 100

@dataclass
class FakutoriOptions(PerGameCommonOptions):
    shop_price: ShopPrice
    death_link: DeathLink
    default_on_toggle: DefaultOnToggle
    start_inventory_from_pool: StartInventoryPool