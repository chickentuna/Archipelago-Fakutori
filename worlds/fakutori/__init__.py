from __future__ import annotations

from dataclasses import dataclass
import os
import collections
import json
import typing
from typing import Any, Dict, List, Optional, Set, Tuple


# see notification class for more details on how to customize notifs

import Utils
from Utils import visualize_regions
from BaseClasses import CollectionState, Region, Location, Item, Tutorial, ItemClassification
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, components, Type, launch as launch_component
from worlds.generic import Rules
from worlds.stardew_valley.stardew_rule import state
from .items import FakutoriItem
from .locations import FakutoriLocation
from .options import FakutoriOptions, VictoryCondition
from .data.data import colors
from worlds.generic.Rules import set_rule, add_rule, forbid_item, add_item_rule
import inspect

def data_path(*args):
    return os.path.join(os.path.dirname(__file__), 'data', *args)

def print_return(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(result)
        return result
    return wrapper

@dataclass
class Ingredient:
    ingredientType: str
    blockName: Optional[str] = None
    property: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[int] = None
@dataclass
class Recipe:
    type: str
    product: str
    ingredients: List[Ingredient]
    byproduct: Optional[str] = None
@dataclass
class BlockData:
    name: str
    id: int
    category: str
    color: str
    properties: List[str]
    unlockedByDefault: bool

class Fakutori(World):
    """Fakutori is a laid-back and colorful automation game;
    place machines, discover new elements, and try to craft the elusive Legendary Blocks!
    No limits, no pressure, just blocks!"""

    game = "Fakutori"  # name of the game/world
    
    required_client_version = (0, 6, 0)
    if Utils.version_tuple < required_client_version:
        raise Exception(f"Update Archipelago to use this world ({game}).")
    
    def __init__(self, world, player: int):
        super(Fakutori, self).__init__(world, player)

    options_dataclass = FakutoriOptions  # options the player can set
    options: FakutoriOptions  # typing hints for option results
    topology_present = True  # show path to required location checks in spoiler

    blocks: List[BlockData] = []
    with open(data_path('blocks.json'), 'r') as stream:
        blocks_json = json.load(stream)
    blocks = [BlockData(**b) for b in blocks_json['blocks']]

    recipes: List[Recipe] = []
    with open(data_path('recipes.json'), 'r') as stream:
        recipes_json = json.load(stream)
    recipes = [
        Recipe(
            type=r["type"],
            product=r["product"],
            byproduct=r["byproduct"],
            ingredients=[Ingredient(**ing) for ing in r["ingredients"]]
        )
        for r in recipes_json["recipes"]
    ]

    item_name_to_id = {}
    location_name_to_id = {}
    for unlockable in blocks:
        item_name_to_id[unlockable.name] = unlockable.id
        if not unlockable.unlockedByDefault and not unlockable.name == 'Disassembler':
            location_name_to_id[unlockable.name] = unlockable.id
    item_name_to_id["500 gold"] = 1000
    item_name_to_id["1000 gold"] = 1001
    item_name_to_id["500 mana"] = 1002
    item_name_to_id["Full starpower"] = 1003

    # Items can be grouped using their names to allow easy checking if any item
    # from that group has been collected. Group names can also be used for !hint
    item_name_groups = {}
    for item in blocks:
        if item.category != 'Machine':
            color = item.color
            if not color in item_name_groups:
                item_name_groups[color] = []
            item_name_groups[color].append(item.name)
        
        for property in item.properties:
            if not property in item_name_groups:
                item_name_groups[property] = []
            item_name_groups[property].append(item.name)

    def classify_item(self, item: str) -> ItemClassification:
        for u in self.blocks:
            if u.name == item:
                if u.category == 'Machine':
                    if 'Generator' in u.name:
                        return ItemClassification.progression 
                    return ItemClassification.useful
                return ItemClassification.progression
        return ItemClassification.filler

    def create_item(self, item: str) -> FakutoriItem:
        classification = self.classify_item(item)
        return FakutoriItem(item, classification, self.item_name_to_id[item], self.player)


    def create_event(self, event: str) -> FakutoriItem:
        # while we are at it, we can also add a helper to create events
        return FakutoriItem(event, ItemClassification.progression, None, self.player)

    def create_items(self) -> None:
        for b in self.blocks:
            if b.name == 'Disassembler':
                continue
            if not b.unlockedByDefault:
                self.multiworld.itempool.append(self.create_item(b.name))
        
        # Add base elements
        for b in self.blocks:
            if b.unlockedByDefault and b.category == 'Raw element':
                self.multiworld.push_precollected(self.create_item(b.name))
        
        # Add base mahchines
        for b in self.blocks:
            if b.unlockedByDefault and b.category == 'Machine':
                if self.options.start_with_base_machines.value:
                    self.multiworld.push_precollected(self.create_item(b.name))
                else:
                    self.multiworld.itempool.append(self.create_item(b.name))
            
        if self.options.start_with_disassembler.value:
            self.multiworld.push_precollected(self.create_item("Disassembler"))
        else:
            self.multiworld.itempool.append(self.create_item("Disassembler"))

        total_locations = len(self.multiworld.get_unfilled_locations(self.player))
        self.multiworld.itempool += [self.create_filler() for _ in range(total_locations - len(self.multiworld.itempool))]
  
    filler_choices = ("Full starpower", "500 mana", "500 gold", "1000 gold")
    filler_weights = (1, 2, 1, 4)

    def get_filler_item_name(self) -> str:
        return self.random.choices(self.filler_choices, self.filler_weights)[0]


    def generate_early(self) -> None:
        # read player options to world instance
        # self.final_boss_hp = self.options.final_boss_hp.value
        pass

    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu_region)  

        main_region = Region("Factory", self.player, self.multiworld)
    
        if not self.options.start_with_disassembler.value:
            self.location_id_to_name[5] = 'Disassembler'
        
        locations = {}
        for location_name in self.location_name_to_id.keys():
            locations[location_name] = self.location_name_to_id[location_name]

        main_region.add_locations(locations, FakutoriLocation)
        #TODO: add the optional challenges

        for i in range(self.options.extra_shop_checks.value):
            main_region.add_locations({f"Extra Shop {i+1}": 1000 + i}, FakutoriLocation)
            self.location_name_to_id[f"Extra Shop {i+1}"] = 1000 + i
        
        self.multiworld.regions.append(main_region)

        menu_region.connect(main_region)

    def can_craft_block(self, state: CollectionState, blockName: str) -> bool:
        every_craftable_block = self.get_every_craftable_block(state)
        return blockName in every_craftable_block


    def get_every_craftable_block(self, state: CollectionState) -> List[str]:
        unlocked_blocks = state.prog_items[self.player].keys()
        return self.get_every_craftable_block_from(unlocked_blocks)
    
    def get_every_craftable_block_from(self, unlocked_blocks: List[str], assume_generators = False) -> List[str]:
        virtual_collection = set()

        unlocked_recipes = []
        for name in unlocked_blocks:
            unlocked_recipes += [r for r in self.recipes if r.product == name]
        for b in self.blocks:
            if b.category == 'Raw element' and b.name in unlocked_blocks and ('Generator ' + b.name.lower() in unlocked_blocks or assume_generators):
                virtual_collection.add(b.name)
        
        new_crafted = True
        while new_crafted:
            new_crafted = False
            for recipe in unlocked_recipes:
                if recipe.product not in virtual_collection and self.can_do_recipe(virtual_collection, recipe):
                    virtual_collection.add(recipe.product)
                    new_crafted = True
                    break
        return virtual_collection

    def has_ingredient(self, collection: Set[str], ingredient: Ingredient) -> bool:
        blockName = ingredient.blockName
        quantity = ingredient.quantity
        ingredientType = ingredient.ingredientType

        if ingredientType == 'Block':
            return blockName in collection
        elif ingredientType == 'Property':
            prop_counter = self.count_properties(collection)
            return prop_counter[ingredient.property] >= quantity
        elif ingredientType == 'Color':
            color_counter = self.count_colors(collection)
            return color_counter[ingredient.color] >= quantity
        return True

    def count_properties(self, collection: Set[str]) -> Dict[str, int]:
        Counter = collections.Counter()
        for block_name in collection:
            block = next(b for b in self.blocks if b.name == block_name)
            for property in block.properties:
                Counter[property] += 1
        return Counter

    def count_colors(self, collection: Set[str]) -> Dict[str, int]:
        Counter = collections.Counter()
        for block_name in collection:
            block = next(b for b in self.blocks if b.name == block_name)
            color = block.color
            if color == 'Colorless':
                for c in colors:
                    Counter[c] += 1
            else:
                Counter[color] += 1
        return Counter

    def can_rainbow(self, collection: Set[str]) -> bool:
        color_counter = self.count_colors(collection)
        return len(color_counter) >= 7

    def can_do_recipe(self, collection: Set[str], recipe: Recipe) -> bool:
        if recipe.type == 'Generator':
            return recipe.product in collection
        if recipe.type == 'Starstruck':
            return "Shooting star" in collection and all(self.has_ingredient(collection, ingredient) for ingredient in recipe.ingredients)
        elif recipe.type == 'Quasar':
            return "Black hole" in collection
        elif recipe.type == 'Void':
            return "Antimatter" in collection
        elif recipe.type == 'EvolvingFire':
            return ("Wood" in collection or "Oil" in collection) and "Fire" in collection
        elif recipe.product == 'Rainbow':
            return self.can_rainbow(collection)
        elif recipe.type in ('Combine', 'Combust', 'Quickening', 'BlackHole', 'Time', 'DissolveMetals', 'Fall'):
            return all(self.has_ingredient(collection, ingredient) for ingredient in recipe.ingredients)
        return True

    def set_rules(self) -> None:
        already_has_rule = set()
        for recipe in self.recipes:
            # Raw Elements do not result in a check
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
                        'or'
                    )
                else:
                    set_rule(
                        self.multiworld.get_location(p, self.player),
                        lambda state, r=recipe: self.can_craft_block(state, r.product)
                    )
                    already_has_rule.add(recipe.product)

    
        if self.options.victory_condition.value == VictoryCondition.option_all_blocks_discovered:
            progression_items = [item.name for item in self.blocks if self.classify_item(item.category) == ItemClassification.progression]
            progression_items_that_are_locations = [item for item in progression_items if item in self.location_name_to_id]
            self.multiworld.completion_condition[self.player] = lambda state,pi=progression_items_that_are_locations: all([loc.name in pi for loc in state.locations_checked])
        elif self.options.victory_condition.value == VictoryCondition.option_spawn_quasar:
            self.multiworld.completion_condition[self.player] = lambda state: any([loc.name == "Quasar" for loc in state.locations_checked])
        else:
            # TODO: challenges
            pass

    def fill_slot_data(self) -> Dict[str, Any]:
        return self.options.as_dict("victory_condition", "shop_price", "extra_shop_checks")
