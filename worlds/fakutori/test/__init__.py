from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from test.bases import WorldTestBase


class MyGameTestBase(WorldTestBase):
    game = "Fakutori"

    def test_beatable(self) -> None:
        self.assertBeatable(True)

    def test_ruby(self) -> None:
        locations = ["Ruby"]
        items = [["Luck", "Stone"]]
        self.assertAccessDependency(locations, items, only_check_listed=True)

    def test_sand(self) -> None:
        locations = ["Sand"]
        items = [["Stone", "Air"]]
        self.assertAccessDependency(locations, items, only_check_listed=True)

    def test_stone(self) -> None:
        locations = ["Stone"]
        items = [["Lava", "Air"]]
        self.assertAccessDependency(locations, items, only_check_listed=True)

    def test_yellow_fire(self) -> None:
        locations = ["Yellow fire"]
        items = [["Wood", "Fire", "Earth", "Water"], ["Oil", "Fire", "Time", "Wood", "Earth"]]
        self.assertAccessDependency(locations, items, only_check_listed=True)
    