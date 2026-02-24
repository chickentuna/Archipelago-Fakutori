from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from test.bases import WorldTestBase


class MyGameTestBase(WorldTestBase):
    game = "Fakutori"

    def test_ruby(self) -> None:
        locations = ["Ruby", "Stone"]
        items = [["Luck", "Air", "Lava"]]
        self.assertAccessDependency(locations, items)

    def test_sand(self) -> None:
        locations = ["Sand"]
        items = [["Air", "Stone"]]
        self.assertAccessDependency(locations, items, only_check_listed=True)

    def test_stone(self) -> None:
        locations = ["Stone"]
        items = [["Air", "Lava"]]
        self.assertAccessDependency(locations, items)

    def test_yellow_fire(self) -> None:
        locations = ["Yellow fire"]
        items = [["Wood"], ["Oil"]]
        self.assertAccessDependency(locations, items, only_check_listed=True)
    