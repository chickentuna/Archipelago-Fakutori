"""Pure crafting simulation used to build Archipelago access rules.

All functions here are standalone (no World instance needed), making them
straightforward to unit-test and to call from both the World class and tests.
"""
from __future__ import annotations

import collections
from typing import Dict, List, Set

from .data.models import BlockData, Ingredient, Recipe
from .constants import COLORS


def get_every_craftable_block_from(
    blocks: List[BlockData],
    recipes: List[Recipe],
    unlocked_blocks,
    assume_generators: bool = False,
) -> Set[str]:
    """Simulate crafting to find every block reachable from the given unlocked set."""
    virtual_collection: Set[str] = set()

    unlocked_recipes = [r for name in unlocked_blocks for r in recipes if r.product == name]

    for b in blocks:
        if (b.category == 'Raw element'
                and b.name in unlocked_blocks
                and ('Generator ' + b.name.lower() in unlocked_blocks or assume_generators)):
            virtual_collection.add(b.name)

    new_crafted = True
    while new_crafted:
        new_crafted = False
        for recipe in unlocked_recipes:
            if recipe.product not in virtual_collection and can_do_recipe(blocks, virtual_collection, recipe):
                virtual_collection.add(recipe.product)
                new_crafted = True
                break

    return virtual_collection


def can_do_recipe(blocks: List[BlockData], collection: Set[str], recipe: Recipe) -> bool:
    """Return True if the given recipe can be performed with the current collection."""
    if recipe.type == 'Generator':
        return recipe.product in collection
    if recipe.type == 'Starstruck':
        return ('Shooting star' in collection
                and all(has_ingredient(blocks, collection, i) for i in recipe.ingredients))
    elif recipe.type == 'Quasar':
        return 'Black hole' in collection
    elif recipe.type == 'Void':
        return 'Antimatter' in collection
    elif recipe.type == 'EvolvingFire':
        return ('Wood' in collection or 'Oil' in collection) and 'Fire' in collection
    elif recipe.product == 'Rainbow':
        return can_rainbow(blocks, collection)
    elif recipe.type in ('Combine', 'Combust', 'Quickening', 'BlackHole', 'Time', 'DissolveMetals', 'Fall'):
        return all(has_ingredient(blocks, collection, i) for i in recipe.ingredients)
    return True


def has_ingredient(blocks: List[BlockData], collection: Set[str], ingredient: Ingredient) -> bool:
    if ingredient.ingredientType == 'Block':
        return ingredient.blockName in collection
    elif ingredient.ingredientType == 'Property':
        return count_properties(blocks, collection)[ingredient.property] >= ingredient.quantity
    elif ingredient.ingredientType == 'Color':
        return count_colors(blocks, collection)[ingredient.color] >= ingredient.quantity
    return True


def count_properties(blocks: List[BlockData], collection: Set[str]) -> Dict[str, int]:
    counter: Dict[str, int] = collections.Counter()
    for block_name in collection:
        block = next(b for b in blocks if b.name == block_name)
        for prop in block.properties:
            counter[prop] += 1
    return counter


def count_colors(blocks: List[BlockData], collection: Set[str]) -> Dict[str, int]:
    counter: Dict[str, int] = collections.Counter()
    for block_name in collection:
        block = next(b for b in blocks if b.name == block_name)
        if block.color == 'Colorless':
            for c in COLORS:
                counter[c] += 1
        else:
            counter[block.color] += 1
    return counter


def can_rainbow(blocks: List[BlockData], collection: Set[str]) -> bool:
    return len(count_colors(blocks, collection)) >= 7
