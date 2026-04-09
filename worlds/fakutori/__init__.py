from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Set

import Utils
from BaseClasses import CollectionState, ItemClassification, Region
from worlds.AutoWorld import World
from worlds.generic.Rules import add_rule, set_rule

from .constants import (
    EXTRA_SHOP_LOCATION_BASE_ID,
    FILLER_1000_GOLD_ID,
    FILLER_500_GOLD_ID,
    FILLER_500_MANA_ID,
    FILLER_FULL_STARPOWER_ID,
)
from .data.models import BlockData, Ingredient, Recipe
from .items import FakutoriItem
from .locations import FakutoriLocation
from .options import FakutoriOptions, VictoryCondition
from . import logic


def data_path(*args: str) -> str:
    return os.path.join(os.path.dirname(__file__), 'data', *args)


class Fakutori(World):
    """Fakutori is a laid-back and colorful automation game;
    place machines, discover new elements, and try to craft the elusive Legendary Blocks!
    No limits, no pressure, just blocks!"""

    game = "Fakutori"
    required_client_version = (0, 6, 0)
    if Utils.version_tuple < required_client_version:
        raise Exception(f"Update Archipelago to use this world ({game}).")

    options_dataclass = FakutoriOptions
    options: FakutoriOptions
    topology_present = True

    # Class-level data: loaded once at import time and shared across all instances.
    with open(data_path('blocks.json'), 'r') as _f:
        blocks: List[BlockData] = [BlockData(**b) for b in json.load(_f)['blocks']]

    with open(data_path('recipes.json'), 'r') as _f:
        recipes: List[Recipe] = [
            Recipe(
                type=r['type'],
                product=r['product'],
                byproduct=r['byproduct'],
                ingredients=[Ingredient(**ing) for ing in r['ingredients']],
            )
            for r in json.load(_f)['recipes']
        ]

    item_name_to_id: Dict[str, int] = {b.name: b.id for b in blocks}
    item_name_to_id.update({
        '500 gold':      FILLER_500_GOLD_ID,
        '1000 gold':     FILLER_1000_GOLD_ID,
        '500 mana':      FILLER_500_MANA_ID,
        'Full starpower': FILLER_FULL_STARPOWER_ID,
    })

    # Locations: non-default blocks, excluding Disassembler and Quasar (handled separately).
    location_name_to_id: Dict[str, int] = {
        b.name: b.id
        for b in blocks
        if not b.unlockedByDefault and b.name not in ('Disassembler', 'Quasar')
    }

    # Item groups by color and property for !hint support.
    item_name_groups: Dict[str, List[str]] = {}
    for _item in blocks:
        if _item.category != 'Machine':
            if _item.color not in item_name_groups:
                item_name_groups[_item.color] = []
            item_name_groups[_item.color].append(_item.name)
        for _prop in _item.properties:
            if _prop not in item_name_groups:
                item_name_groups[_prop] = []
            item_name_groups[_prop].append(_item.name)

    filler_choices = ('Full starpower', '500 mana', '500 gold', '1000 gold')
    filler_weights = (1, 2, 1, 4)

    def __init__(self, world, player: int):
        super().__init__(world, player)

    def classify_item(self, item: str) -> ItemClassification:
        for b in self.blocks:
            if b.name == item:
                if b.category == 'Machine':
                    if 'Generator' in b.name:
                        return ItemClassification.progression
                    return ItemClassification.useful
                return ItemClassification.progression
        return ItemClassification.filler

    def create_item(self, item: str) -> FakutoriItem:
        return FakutoriItem(item, self.classify_item(item), self.item_name_to_id[item], self.player)

    def create_event(self, event: str) -> FakutoriItem:
        return FakutoriItem(event, ItemClassification.progression, None, self.player)

    def get_filler_item_name(self) -> str:
        return self.random.choices(self.filler_choices, self.filler_weights)[0]

    def create_items(self) -> None:
        for b in self.blocks:
            if b.name == 'Disassembler':
                continue  # handled separately below

            if b.unlockedByDefault:
                if b.category == 'Raw element':
                    self.multiworld.push_precollected(self.create_item(b.name))
                elif b.category == 'Machine':
                    if self.options.start_with_base_machines.value:
                        self.multiworld.push_precollected(self.create_item(b.name))
                    else:
                        self.multiworld.itempool.append(self.create_item(b.name))
            else:
                self.multiworld.itempool.append(self.create_item(b.name))

        # Disassembler has its own option, independent of start_with_base_machines.
        if self.options.start_with_disassembler.value:
            self.multiworld.push_precollected(self.create_item('Disassembler'))
        else:
            self.multiworld.itempool.append(self.create_item('Disassembler'))

        total_locations = len(self.multiworld.get_unfilled_locations(self.player))
        self.multiworld.itempool += [self.create_filler() for _ in range(total_locations - len(self.multiworld.itempool))]

    def create_regions(self) -> None:
        menu_region = Region('Menu', self.player, self.multiworld)
        self.multiworld.regions.append(menu_region)

        main_region = Region('Factory', self.player, self.multiworld)

        if not self.options.start_with_disassembler.value:
            self.location_id_to_name[5] = 'Disassembler'

        if self.options.victory_condition.value != VictoryCondition.option_spawn_quasar:
            self.location_id_to_name[50] = 'Quasar'

        main_region.add_locations(dict(self.location_name_to_id), FakutoriLocation)
        # TODO: add optional block challenges

        if self.options.victory_condition.value == VictoryCondition.option_spawn_quasar:
            main_region.locations.append(FakutoriLocation(self.player, 'Quasar', None, main_region))

        for i in range(self.options.extra_shop_checks.value):
            loc_name = f'Extra shop {i + 1}'
            loc_id = EXTRA_SHOP_LOCATION_BASE_ID + i
            main_region.add_locations({loc_name: loc_id}, FakutoriLocation)
            self.location_name_to_id[loc_name] = loc_id

        self.multiworld.regions.append(main_region)
        menu_region.connect(main_region)

    def set_rules(self) -> None:
        self._set_location_rules()
        self._set_completion_condition()

    def _set_location_rules(self) -> None:
        already_has_rule: Set[str] = set()

        for recipe in self.recipes:
            # Raw elements are pre-collected, not check locations.
            if recipe.product in ('Water', 'Air', 'Fire', 'Earth'):
                continue

            products = [recipe.product]
            if recipe.byproduct:
                products.append(recipe.byproduct)

            for p in products:
                if p in already_has_rule:
                    add_rule(
                        self.multiworld.get_location(p, self.player),
                        lambda state, r=recipe: self.can_craft_block(state, r.product),
                        'or',
                    )
                else:
                    set_rule(
                        self.multiworld.get_location(p, self.player),
                        lambda state, r=recipe: self.can_craft_block(state, r.product),
                    )
                    already_has_rule.add(recipe.product)

    def _set_completion_condition(self) -> None:
        condition = self.options.victory_condition.value

        if condition == VictoryCondition.option_all_elements_discovered:
            element_locations = [
                b.name for b in self.blocks
                if b.category != 'Machine' and not b.unlockedByDefault
            ]
            self.multiworld.completion_condition[self.player] = lambda state: all(
                loc in {l.name for l in state.locations_checked}
                for loc in element_locations
            )
        elif condition == VictoryCondition.option_spawn_quasar:
            self.multiworld.get_location('Quasar', self.player).place_locked_item(self.create_event('Victory'))
            self.multiworld.completion_condition[self.player] = lambda state: state.has('Victory', self.player)
        # VictoryCondition.option_all_block_challenges: not yet implemented

    def fill_slot_data(self) -> Dict[str, Any]:
        return self.options.as_dict(
            'victory_condition', 'shop_price', 'extra_shop_checks',
            'start_with_disassembler', 'start_with_base_machines',
        )

    # --- Crafting simulation (thin wrappers around the logic module) ---

    def can_craft_block(self, state: CollectionState, block_name: str) -> bool:
        return block_name in self.get_every_craftable_block(state)

    def get_every_craftable_block(self, state: CollectionState) -> Set[str]:
        return self.get_every_craftable_block_from(state.prog_items[self.player].keys())

    def get_every_craftable_block_from(self, unlocked_blocks, assume_generators: bool = False) -> Set[str]:
        return logic.get_every_craftable_block_from(
            self.blocks, self.recipes, unlocked_blocks, assume_generators,
        )
