from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


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
