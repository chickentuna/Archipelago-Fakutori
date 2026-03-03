from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from test.bases import WorldTestBase


class MyGameTestBase(WorldTestBase):
    game = "Fakutori"

    def test_fire(self) -> None:
        unlocks = ['Fire', 'Earth', 'Water', 'Wood', 'Yellow fire', 'Blue fire', 'Air']
        all_craftable = self.world.get_every_craftable_block_from(unlocks)
        print(all_craftable)
        assert all_craftable == {'Fire', 'Wood', 'Earth', 'Air', 'Blue fire', 'Water', 'Yellow fire'}
    
    def test_no_wood(self) -> None:
        unlocks = ['Fire', 'Earth', 'Wood', 'Yellow fire', 'Blue fire']
        all_craftable = self.world.get_every_craftable_block_from(unlocks)
        print(all_craftable)
        assert all_craftable == {'Fire', 'Earth'}
    
    def test_time(self) -> None:
        unlocks = ['Time', 'Fire', 'Water', 'Smoke', 'Steam', 'Ether']
        all_craftable = self.world.get_every_craftable_block_from(unlocks)
        print(all_craftable)
        assert all_craftable == {'Time', 'Fire', 'Water', 'Steam', 'Ether'}
    
    def test_no_rainbow(self) -> None:
        unlocks_no_pink = [
            'Lava', 'Fire', # orange
            'Water', # blue
            'Smoke', 'Wood', 'Earth', # brown
            'Steam', 'Air', # white
            'Stone', # grey            
            'Shooting star', # yellow
            'Rainbow'
        ]
        all_craftable_no_pink = self.world.get_every_craftable_block_from(unlocks_no_pink)
        assert "Rainbow" not in all_craftable_no_pink

    def test_lava(self) -> None:
        locations = ["Lava"]
        items = [["Lava"]]
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
    
    def test_rainbow(self) -> None:
        unlocks_with_pink = [
            'Lava', 'Fire', # orange
            'Water', # blue
            'Smoke', 'Wood', 'Earth', # brown
            'Steam', 'Air', # white
            'Stone', # grey            
            'Shooting star', # yellow
            'Ether', # pink
            'Rainbow'
        ]
        all_craftable_with_pink = self.world.get_every_craftable_block_from(unlocks_with_pink)
        print(all_craftable_with_pink)
        assert "Rainbow" in all_craftable_with_pink
