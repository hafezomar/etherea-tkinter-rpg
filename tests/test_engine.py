from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from random import Random
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from game.engine import GameState
from game.map_data import build_rooms
from game.models import EnemyKind, HeroClass


class TkinterGameTests(unittest.TestCase):
    def test_all_rooms_are_rectangular(self) -> None:
        rooms = build_rooms()
        self.assertEqual(len(rooms), 4)
        for room in rooms:
            self.assertEqual(room.width, 18)
            self.assertEqual(room.height, 12)

    def test_starting_class_is_created(self) -> None:
        state = GameState(Random(5))
        state.start(HeroClass.WARDEN)
        self.assertEqual(state.player.hero_class, HeroClass.WARDEN)
        self.assertEqual(state.player.hp, state.player.max_hp)
        self.assertEqual(state.mode, "playing")

    def test_attack_damages_adjacent_enemy(self) -> None:
        state = GameState(Random(3))
        state.start(HeroClass.ASHEN_BLADE)
        enemy = state.room.enemies[0]
        enemy.x = state.player.x + 1
        enemy.y = state.player.y
        before = enemy.hp
        state.attack()
        self.assertLess(enemy.hp, before)

    def test_save_and_load_preserve_progress(self) -> None:
        state = GameState(Random(7))
        state.start(HeroClass.DREAMSEER)
        state.player.shards = 19
        state.room_index = 1
        state.player.x, state.player.y = state.room.start
        with tempfile.TemporaryDirectory() as temporary_directory:
            save_path = Path(temporary_directory) / "blood_wing.json"
            state.save(save_path)
            loaded = GameState.load(save_path, Random(7))
        self.assertEqual(loaded.room_index, 1)
        self.assertEqual(loaded.player.shards, 19)
        self.assertEqual(loaded.player.hero_class, HeroClass.DREAMSEER)

    def test_final_room_contains_vaelrith(self) -> None:
        final_room = build_rooms()[-1]
        self.assertEqual(final_room.enemies[0].kind, EnemyKind.VAELRITH)

    def test_shrine_choice_can_grant_focus_and_potion(self) -> None:
        state = GameState(Random(4))
        state.start(HeroClass.DREAMSEER)
        shrine_x, shrine_y = next(
            (x, y)
            for y, row in enumerate(state.room.tiles)
            for x, tile in enumerate(row)
            if tile == "†"
        )
        state.player.x, state.player.y = shrine_x, shrine_y
        state._resolve_tile()
        before_potions = state.player.potions
        state.choose_shrine("focus")
        self.assertIsNone(state.pending_choice)
        self.assertEqual(state.player.potions, before_potions + 1)
        self.assertEqual(state.room.tile_at(shrine_x, shrine_y), ".")

    def test_shop_can_trade_shards_for_potion_and_advance(self) -> None:
        state = GameState(Random(6))
        state.start(HeroClass.WARDEN)
        state.room.enemies.clear()
        exit_x, exit_y = next(
            (x, y)
            for y, row in enumerate(state.room.tiles)
            for x, tile in enumerate(row)
            if tile == ">"
        )
        state.player.x, state.player.y = exit_x, exit_y
        state.player.shards = 30
        before_potions = state.player.potions
        state._resolve_tile()
        state.choose_shop("buy")
        self.assertEqual(state.room_index, 1)
        self.assertEqual(state.player.shards, 0)
        self.assertEqual(state.player.potions, before_potions + 1)

    def test_vaelrith_summons_two_pilgrims_when_space_allows(self) -> None:
        state = GameState(Random(9))
        state.start(HeroClass.WARDEN)
        state.room_index = len(state.rooms) - 1
        state.player.x, state.player.y = state.room.start
        boss = state.room.enemies[0]
        state._summon_pilgrim(boss)
        pilgrims = [enemy for enemy in state.room.living_enemies() if enemy.kind == EnemyKind.FALSE_PILGRIM]
        self.assertEqual(len(pilgrims), 2)


if __name__ == "__main__":
    unittest.main()
