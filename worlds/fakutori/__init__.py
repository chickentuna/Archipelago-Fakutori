from __future__ import annotations

import os
import collections
import json
import typing
from typing import Any, Dict, List, Optional, Tuple


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
from .options import FakutoriOptions
from .data.data import colors
from worlds.generic.Rules import add_rule, set_rule, forbid_item, add_item_rule

def data_path(*args):
    return os.path.join(os.path.dirname(__file__), 'data', *args)

def print_return(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(result)
        return result
    return wrapper


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

    blocks = []
    with open(data_path('blocks.json'), 'r') as stream:
        blocks_json = json.load(stream)
    blocks = [b for b in blocks_json['blocks'] if 'Generator' not in b['name']]

    recipes = []
    with open(data_path('recipes.json'), 'r') as stream:
        recipes_json = json.load(stream)
    recipes = [r for r in recipes_json['recipes'] if r['type'] != 'Generator']
    for c in colors:
        recipes.append({
            "type": "Combine",
            "product": f"Quartz {c.lower()}",
            "ingredients": [
                {
                "blockName": "Sand",
                "quantity": 1,
                "ingredientType": "Block"
                },
                {
                "blockName": "Time",
                "quantity": 1,
                "ingredientType": "Block"
                }
            ]
        })


    item_name_to_id = {}
    location_name_to_id = {}
    for unlockable in blocks:
        item_name_to_id[unlockable['name']] = unlockable['id']
        if not unlockable['unlockedByDefault']:
            location_name_to_id[unlockable['name']] = unlockable['id']
    item_name_to_id["nothing"] = 999  # for junk filling
    # TODO: replace/add coins/mana/star power
    

    # Items can be grouped using their names to allow easy checking if any item
    # from that group has been collected. Group names can also be used for !hint
    item_name_groups = {}
    for item in blocks:
        if item['category'] != 'Machine':
            color = item['color']
            if not color in item_name_groups:
                item_name_groups[color] = []
            item_name_groups[color].append(item['name'])
        
        for property in item['properties']:
            if not property in item_name_groups:
                item_name_groups[property] = []
            item_name_groups[property].append(item['name'])

    def classify_item(self, item: str) -> ItemClassification:
        for u in self.blocks:
            if u['name'] == item:
                if u['category'] == 'Machine':
                    return ItemClassification.useful
                return ItemClassification.progression
        return ItemClassification.filler

    def create_item(self, item: str) -> FakutoriItem:
        # this is called when AP wants to create an item by name (for plando, start inventory, item links) or when you call it from your own code
        classification = self.classify_item(item)
        return FakutoriItem(item, classification, self.item_name_to_id[item], self.player)


    def create_event(self, event: str) -> FakutoriItem:
        # while we are at it, we can also add a helper to create events
        return FakutoriItem(event, ItemClassification.progression, None, self.player)

    def create_items(self) -> None:
        # Add items to the Multiworld.
        # If there are two of the same item, the item has to be twice in the pool.
        # Which items are added to the pool may depend on player options, e.g. custom win condition like triforce hunt.
        # Having an item in the start inventory won't remove it from the pool.
        # If you want to do that, use start_inventory_from_pool

        for b in self.blocks:
            if not b['unlockedByDefault']:
                self.multiworld.itempool.append(self.create_item(b['name']))

        # itempool and number of locations should match up.
        # If this is not the case we want to fill the itempool with junk.
        junk = 0  # calculate this based on player options
        self.multiworld.itempool += [self.create_item("nothing") for _ in range(junk)]
        for b in self.blocks:
            if b['unlockedByDefault']:
                self.multiworld.push_precollected(self.create_item(b['name']))


    def generate_early(self) -> None:
        # read player options to world instance
        # self.final_boss_hp = self.options.final_boss_hp.value
        pass

    def create_regions(self) -> None:
        # Add regions to the multiworld. One of them must use the origin_region_name as its name ("Menu" by default).
        # Arguments to Region() are name, player, multiworld, and optionally hint_text
        menu_region = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu_region)  # or use += [menu_region...]

        main_region = Region("Factory", self.player, self.multiworld)
        # add main area's locations to main area (all but final boss)
    
        locations = {}
        # for unlockable in [u for u in self.blocks if not u['default']]:
        for location_name in self.location_name_to_id.keys():
            locations[location_name] = self.location_name_to_id[location_name]

        main_region.add_locations(locations, FakutoriLocation)
        #TODO: add the optional challenges
        
        self.multiworld.regions.append(main_region)

        menu_region.connect(main_region) 

    def can_craft_block(self, state: CollectionState, blockName: str) -> bool:
        every_craftable_block = self.get_every_craftable_block(state)
        return blockName in every_craftable_block


    def get_every_craftable_block(self, state: CollectionState) -> List[str]:
        unlocked_recipes = []
        for name in state.prog_items[self.player]:
            unlocked_recipes += [r for r in self.recipes if r['product'] == name]
        virtual_collection = ['Fire', 'Water', 'Earth', 'Air']
        to_add = []
        new_crafted = True
        while new_crafted:
            new_crafted = False
            for recipe in unlocked_recipes:
                if recipe["product"] not in virtual_collection and self.can_do_recipe(virtual_collection, recipe):
                    to_add.append(recipe['product'])
                    new_crafted = True
                    break
            virtual_collection += to_add
        return virtual_collection

    def has_ingredient(self, collection: List[str], ingredient) -> bool:
        blockName = ingredient['blockName']
        quantity = ingredient['quantity']
        ingredientType = ingredient['ingredientType']

        if ingredientType == 'Block':
            return blockName in collection
        elif ingredientType == 'Property':
            prop_counter = self.count_properties(collection)
            return prop_counter[ingredient['property']] >= quantity
        elif ingredientType == 'Color':
            color_counter = self.count_colors(collection)
            return color_counter[ingredient['color']] >= quantity
        return True

    def count_properties(self, collection: List[str]) -> Dict[str, int]:
        Counter = collections.Counter()
        for block_name in collection:
            block = next(b for b in self.blocks if b['name'] == block_name)
            for property in block['properties']:
                if block_name in collection:
                    Counter[property] += 1
        return Counter

    def count_colors(self, collection: List[str]) -> Dict[str, int]:
        Counter = collections.Counter()
        for block_name in collection:
            block = next(b for b in self.blocks if b['name'] == block_name)
            color = block['color']
            if block_name in collection:
                Counter[color] += 1
        return Counter

    def can_rainbow(self, collection: List[str]) -> bool:
        color_counter = self.count_colors(collection)
        return len(color_counter) >= 7

    def can_do_recipe(self, collection: List[str], recipe) -> bool:
        if recipe['type'] == 'Starstruck':
            return "Shooting star" in collection and all(self.has_ingredient(collection, ingredient) for ingredient in recipe['ingredients'])
        elif recipe['type'] == 'Quasar':
            return "Black hole" in collection
        elif recipe['type'] == 'Void':
            return "Antimatter" in collection
        elif recipe['type'] == 'EvolvingFire':
            return "Wood" in collection or "Oil" in collection and "Fire" in collection
        elif recipe['product'] == 'Rainbow':
            return self.can_rainbow(collection)
        elif recipe['type'] in ('Combine', 'Combust', 'Quickening', 'BlackHole', 'Time', 'DissolveMetals', 'Fall'):
            return all(self.has_ingredient(collection, ingredient) for ingredient in recipe['ingredients'])
        return True

    def set_rules(self) -> None:
        for recipe in self.recipes:
            set_rule(
                self.multiworld.get_location(recipe['product'], self.player),
                lambda state, r=recipe: self.can_craft_block(state, r['product'])
            )
        
        progression_items = [item['name'] for item in self.blocks if self.classify_item(item['category']) == ItemClassification.progression]
        self.multiworld.completion_condition[self.player] = lambda state: state.has_all(progression_items, self.player)
        