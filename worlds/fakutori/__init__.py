from __future__ import annotations

import os
import collections
import inspect
import json
import logging
import typing
from typing import Any, Dict, List, Optional, Tuple

# todo use AbstractSingleton<Notifications>.Instance.QueueNotification(NotificationType.NewBlock, blockData, onCell);
# see notification class for more details on how to customize notifs

import Utils
from Utils import visualize_regions
from BaseClasses import CollectionState, Region, Location, Item, Tutorial, ItemClassification
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, components, Type, launch as launch_component
from worlds.generic import Rules
from .items import FakutoriItem
from .locations import FakutoriLocation
from .options import FakutoriOptions
from settings import Group
from .data import blocks, name_to_color, colors, metals
from worlds.generic.Rules import add_rule, set_rule, forbid_item, add_item_rule

def data_path(*args):
    return os.path.join(os.path.dirname(__file__), *args)

class FakutoriSettings(Group):
    pass

class Fakutori(World):
    """Fakutori is a laid-back and colorful automation game;
    place machines, discover new elements, and try to craft the elusive Legendary Blocks!
    No limits, no pressure, just blocks!"""

    
    required_client_version = (0, 6, 0)
    if Utils.version_tuple < required_client_version:
        raise Exception(f"Update Archipelago to use this world ({game}).")
    
    def __init__(self, world, player: int):
        super(Fakutori, self).__init__(world, player)

    game = "Fakutori"  # name of the game/world
    options_dataclass = FakutoriOptions  # options the player can set
    options: FakutoriOptions  # typing hints for option results
    settings: typing.ClassVar[FakutoriSettings]  # will be automatically assigned from type hint
    topology_present = True  # show path to required location checks in spoiler

    base_id = 0
    # instead of dynamic numbering, IDs could be part of data

    # The following two dicts are required for the generation to know which
    # items exist. They could be generated from json or something else. They can
    # include events, but don't have to since events will be placed manually.
    unlockables = [b for b in blocks if not b['default']]  # this is the list of items that can be placed in the item pool, e.g. for progression or as filler. It should include all items that can be found in locations, but may also include items that are only in the item pool and not found in locations, e.g. because they are only in the starting inventory or because they are used as crafting ingredients but not found directly in locations.
    
    item_name_to_id = {}
    location_name_to_id = {}
    for unlockable in unlockables:
        item_name_to_id[unlockable['name']] = unlockable['id']
        location_name_to_id[unlockable['name']] = unlockable['id']
    item_name_to_id["nothing"] = 999  # for junk filling
    # TODO: replace with coins/mana/star power
    

    # Items can be grouped using their names to allow easy checking if any item
    # from that group has been collected. Group names can also be used for !hint
    item_name_groups = {}
    for item in unlockables:
        if item['category'] != 'Machine':
            color = name_to_color[item['name']]
            if not color in item_name_groups:
                item_name_groups[color] = []
            item_name_groups[color].append(item['name'])
    item_name_groups['Metals'] = metals


    def classify_item(self, item: str) -> ItemClassification:
        for u in self.unlockables:
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

        for item in map(lambda x: self.create_item(x['name']), self.unlockables):
            self.multiworld.itempool.append(item)

        # itempool and number of locations should match up.
        # If this is not the case we want to fill the itempool with junk.
        junk = 0  # calculate this based on player options
        self.multiworld.itempool += [self.create_item("nothing") for _ in range(junk)]

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
        for unlockable in self.unlockables:
            locations.update({unlockable['name']: self.location_name_to_id[unlockable['name']]})
        #TODO: what are events and should i put items in locations?

        main_region.add_locations(locations, FakutoriLocation)
        #TODO: add the optional challenges
        
        self.multiworld.regions.append(main_region)

        menu_region.connect(main_region) 

    def has_ingredient(self, state: CollectionState, ingredient) -> bool:
        blockName = ingredient['blockName']
        quantity = ingredient['quantity']
        ingredientType = ingredient['ingredientType']

        base_blocks = ['Fire', 'Water', 'Earth', 'Air']

        if ingredientType == 'Block':
            if blockName in base_blocks:
                return True
            return state.has(blockName, self.player, 1)
        elif ingredientType == 'Color':
            return state.has_group_unique(ingredient['color'], self.player, quantity)
        
        return True

    def can_rainbow(self, state: CollectionState) -> bool:
        n = 0
        default_colors = ['Blue', 'Red', 'Brown', 'White']
        for color in colors:
            if color in default_colors or state.count_group_unique(color, self.player) > 0:
                n += 1
        return n >= 7

    # TODO: check entire recipe tree, also remove machiens from the pool for now!
    def set_rules(self) -> None:
        items_with_no_rule = set()

        for item in self.unlockables:
            if item['category'] != 'Machine':
                set_rule(
                    self.multiworld.get_location(item['name'], self.player),
                    lambda state: False
                )
                items_with_no_rule.add(item['name'])
        
        recipes_json = []
        with open(data_path('recipes.json'), 'r') as stream:
            recipes_json = json.load(stream)
        recipes = recipes_json['recipes']
        for recipe in recipes:
            if recipe['product'] == 'Electricity':
                add_rule(
                    self.multiworld.get_location('Electricity', self.player),
                    lambda state: state.has_any(["Acid"], self.player) and state.has_group("Metals", self.player),
                    "or"
                )
                items_with_no_rule.discard('Electricity')

            elif recipe['type'] == 'Quasar':
                add_rule(
                    self.multiworld.get_location('Quasar', self.player),
                    lambda state: state.has_any(["Black hole"], self.player),
                    "or"
                )
                items_with_no_rule.discard('Quasar')
            elif recipe['type'] == 'Void':
                add_rule(
                    self.multiworld.get_location('Void', self.player),
                    lambda state: state.has_any(["Antimatter"], self.player),
                    "or"
                )
                items_with_no_rule.discard('Void')
            elif recipe['type'] == 'EvolvingFire':
                product = 'Yellow fire' if recipe['product'] == 'Fire 2' else 'Blue fire'
                add_rule(
                    self.multiworld.get_location(product, self.player),
                    lambda state: state.has_any(["Wood", "Oil"], self.player),
                    "or"
                )
                items_with_no_rule.discard(product)
                print(f"Added rule for {product} requiring Wood or Oil")
            elif recipe['product'] == 'Rainbow':
                add_rule(
                    self.multiworld.get_location('Rainbow', self.player),
                    lambda state: self.can_rainbow(state),
                    "or"
                )
                items_with_no_rule.discard('Rainbow')
            elif recipe['type'] in ('Combine', 'Combust', 'Quickening', 'Black hole'):
                print(f"Adding rule for {recipe['product']} requiring {[i['blockName'] for i in recipe['ingredients']]}")
                add_rule(
                    self.multiworld.get_location(recipe['product'], self.player),
                    lambda state, r=recipe: all(self.has_ingredient(state, ingredient) for ingredient in r['ingredients']),
                    "or"
                )

                items_with_no_rule.discard(recipe['product'])
        for item in items_with_no_rule:
            print(item, 'is accessible')
            set_rule(
                self.multiworld.get_location(item, self.player),
                lambda state: True
            )
        self.multiworld.get_location("Quasar", self.player).place_locked_item(self.create_item("Quasar"))
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Quasar", self.player)