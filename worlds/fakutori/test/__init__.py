from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from test.bases import WorldTestBase


class MyGameTestBase(WorldTestBase):
    game = "Fakutori"

    # def test_ruby(self) -> None:
    #     locations = ["Ruby"]
    #     items = [["Stone", "Luck"]]
    #     self.assertAccessDependency(locations, items)

    def test_sand(self) -> None:
        locations = ["Sand"]
        items = [["Air", "Stone"]]
        self.assertAccessDependency(locations, items)
    
    # def test_wood(self) -> None:
    #     locations = ["Wood"]
    #     items = []
    #     self.assertAccessDependency(locations, items)