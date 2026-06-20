from __future__ import annotations

import json
from pathlib import Path
from random import Random

from game.map_data import build_rooms, make_enemy
from game.models import Enemy, EnemyKind, HeroClass, Player, RoomState


class GameState:
    def __init__(self, rng: Random | None = None) -> None:
        self.rng = rng or Random()
        self.rooms: list[RoomState] = build_rooms()
        self.room_index = 0
        self.player: Player | None = None
        self.events: list[str] = []
        self.mode = "class_select"
        self.pending_choice: str | None = None

    @property
    def room(self) -> RoomState:
        return self.rooms[self.room_index]

    def start(self, hero_class: HeroClass) -> None:
        self.room_index = 0
        self.rooms = build_rooms()
        start_x, start_y = self.room.start
        self.player = Player.create(hero_class, start_x, start_y)
        self.mode = "playing"
        self.events = []
        self.pending_choice = None
        self.log(f"You enter the Temple of the Sleepers as a {hero_class.value}.")
        self.log(self.room.subtitle)

    def log(self, message: str) -> None:
        self.events.append(message)
        self.events = self.events[-8:]

    def objective(self) -> str:
        if self.mode == "victory":
            return "The First Seal is broken."
        if self.mode == "defeat":
            return "The Blood Wing remembers your name."
        if self.room_index == len(self.rooms) - 1:
            return "Defeat Vaelrith, Herald of the First Seal."
        if self.room.living_enemies():
            return "Clear the chamber before seeking the next door."
        return "Find the gold exit tile and move deeper into the Blood Wing."

    def move(self, dx: int, dy: int) -> None:
        if self.mode != "playing" or self.player is None or self.pending_choice is not None:
            return
        target_x = self.player.x + dx
        target_y = self.player.y + dy
        if not self._inside(target_x, target_y) or self.room.tile_at(target_x, target_y) == "#":
            self.log("The temple wall does not move.")
            return
        enemy = self._enemy_at(target_x, target_y)
        if enemy:
            self._player_attack(enemy)
            self._advance_turn()
            return
        self.player.x = target_x
        self.player.y = target_y
        self._resolve_tile()
        if self.mode == "playing" and self.pending_choice is None:
            self._advance_turn()

    def attack(self) -> None:
        if self.mode != "playing" or self.player is None or self.pending_choice is not None:
            return
        enemy = self._nearest_enemy(1)
        if enemy is None:
            self.log("No enemy is close enough to strike.")
            return
        self._player_attack(enemy)
        self._advance_turn()

    def choose_shrine(self, choice: str) -> None:
        if self.player is None or self.pending_choice != "shrine":
            return
        if choice == "health":
            healed = min(16, self.player.max_hp - self.player.hp)
            self.player.hp += healed
            self.log(f"The saint shrine restores {healed} HP.")
        elif choice == "focus":
            focus = min(6, self.player.max_focus - self.player.focus)
            self.player.focus += focus
            self.player.potions += 1
            self.log(f"The saint shrine restores {focus} focus and grants a Blood Vial.")
        else:
            return
        self.room.set_tile(self.player.x, self.player.y, ".")
        self.pending_choice = None
        self._advance_turn()

    def choose_shop(self, choice: str) -> None:
        if self.player is None or self.pending_choice != "shop":
            return
        if choice == "buy":
            if self.player.shards < 30:
                self.log("The reliquary merchant asks for 30 relic shards.")
                return
            self.player.shards -= 30
            self.player.potions += 1
            self.log("You spend 30 relic shards for a Blood Vial.")
        else:
            self.log("You keep your relic shards and move on.")
        self.pending_choice = None
        self._advance_room()

    def special(self) -> None:
        if self.mode != "playing" or self.player is None or self.pending_choice is not None:
            return
        player = self.player
        if player.hero_class == HeroClass.WARDEN:
            if player.focus < 3:
                self.log("Shield Bash needs 3 focus.")
                return
            enemy = self._nearest_enemy(1)
            if enemy is None:
                self.log("Shield Bash needs an enemy beside you.")
                return
            player.focus -= 3
            self._player_attack(enemy, bonus=6)
            enemy.stun_turns = 1
            self.log(f"{enemy.kind.value} is staggered by Shield Bash.")
        elif player.hero_class == HeroClass.ASHEN_BLADE:
            if player.focus < 4:
                self.log("Cinder Arc needs 4 focus.")
                return
            nearby = [enemy for enemy in self.room.living_enemies() if self._distance(player.x, player.y, enemy.x, enemy.y) <= 1]
            if not nearby:
                self.log("Cinder Arc needs an enemy beside you.")
                return
            player.focus -= 4
            for enemy in nearby:
                self._player_attack(enemy, bonus=4, quiet=True)
                enemy.bleed_turns = max(enemy.bleed_turns, 3)
            self.log("Cinder Arc cuts a red circle through the nearby enemies.")
        else:
            if player.focus < 4:
                self.log("Dream Lance needs 4 focus.")
                return
            enemy = self._nearest_enemy(4)
            if enemy is None:
                self.log("Dream Lance cannot find a target nearby.")
                return
            player.focus -= 4
            self._player_attack(enemy, bonus=8)
            enemy.stun_turns = 1
            self.log("A pale lance of dream-light pins the enemy in place.")
        self._advance_turn()

    def use_potion(self) -> None:
        if self.mode != "playing" or self.player is None or self.pending_choice is not None:
            return
        if self.player.potions <= 0:
            self.log("Your satchel holds no Blood Vials.")
            return
        self.player.potions -= 1
        before = self.player.hp
        self.player.hp = min(self.player.max_hp, self.player.hp + 24)
        self.log(f"The Blood Vial restores {self.player.hp - before} HP.")
        self._advance_turn()

    def rest(self) -> None:
        if self.mode != "playing" or self.player is None or self.pending_choice is not None:
            return
        restored = min(2, self.player.max_focus - self.player.focus)
        self.player.focus += restored
        self.log(f"You steady your breath and recover {restored} focus.")
        self._advance_turn()

    def _resolve_tile(self) -> None:
        if self.player is None:
            return
        tile = self.room.tile_at(self.player.x, self.player.y)
        if tile == "~":
            self.player.hp = max(0, self.player.hp - 3)
            self.log("Blood rises through the cracks. You take 3 damage.")
        elif tile == "!":
            self.room.set_tile(self.player.x, self.player.y, ".")
            self.player.potions += 1
            shards = self.rng.randint(8, 14)
            self.player.shards += shards
            self.log(f"You open a reliquary: Blood Vial +1, relic shards +{shards}.")
        elif tile == "†":
            self.pending_choice = "shrine"
            self.log("The saint shrine offers a choice: health, or focus with a Blood Vial.")
        elif tile == ">":
            if self.room.living_enemies():
                self.log("The gold door is sealed while enemies remain.")
            else:
                self.pending_choice = "shop"
                self.log("A reliquary merchant waits at the threshold. Spend 30 shards for a Blood Vial?")

    def _advance_room(self) -> None:
        if self.room_index >= len(self.rooms) - 1:
            return
        self.room.cleared = True
        self.room_index += 1
        next_room = self.room
        if self.player is not None:
            self.player.x, self.player.y = next_room.start
        self.log(f"You enter {next_room.name}.")
        self.log(next_room.subtitle)

    def _advance_turn(self) -> None:
        if self.player is None or not self.player.alive:
            self._defeat()
            return
        if self.player.bleed_turns > 0:
            self.player.bleed_turns -= 1
            self.player.hp = max(0, self.player.hp - 2)
            self.log("You bleed for 2 damage.")
        if self.player.empowered_turns > 0:
            self.player.empowered_turns -= 1
        self._enemy_turns()
        if self.player.hp <= 0:
            self._defeat()

    def _enemy_turns(self) -> None:
        if self.player is None:
            return
        for enemy in list(self.room.living_enemies()):
            if enemy.bleed_turns > 0:
                enemy.bleed_turns -= 1
                enemy.hp = max(0, enemy.hp - 3)
                self.log(f"{enemy.kind.value} bleeds for 3 damage.")
                if not enemy.alive:
                    self._defeat_enemy(enemy)
                    continue
            if enemy.stun_turns > 0:
                enemy.stun_turns -= 1
                self.log(f"{enemy.kind.value} is staggered.")
                continue
            distance = self._distance(enemy.x, enemy.y, self.player.x, self.player.y)
            if distance <= 1:
                self._enemy_attack(enemy)
            else:
                self._move_enemy(enemy)

    def _player_attack(self, enemy: Enemy, bonus: int = 0, quiet: bool = False) -> None:
        if self.player is None:
            return
        raw = self.player.attack_value() + bonus + self.rng.randint(-2, 3) - enemy.defense
        critical = self.rng.random() < 0.14
        damage = max(1, round(raw * (1.55 if critical else 1)))
        enemy.hp = max(0, enemy.hp - damage)
        if not quiet:
            ending = " Critical hit." if critical else ""
            self.log(f"You strike {enemy.kind.value} for {damage} damage.{ending}")
        if not enemy.alive:
            self._defeat_enemy(enemy)

    def _enemy_attack(self, enemy: Enemy) -> None:
        if self.player is None:
            return
        multiplier = 1.0
        health_ratio = enemy.hp / enemy.max_hp
        if enemy.kind == EnemyKind.VAELRITH:
            if health_ratio <= 0.25:
                multiplier = 1.65
                if enemy.phase_announced < 3:
                    enemy.phase_announced = 3
                    self.log("Vaelrith enters the third phase. The First Seal tears wider.")
            elif health_ratio <= 0.50:
                multiplier = 1.35
                if enemy.phase_announced < 2:
                    enemy.phase_announced = 2
                    self.log("Vaelrith opens the Blood Wing beneath the arena.")
                if not enemy.summoned and self.rng.random() < 0.30:
                    enemy.summoned = True
                    self._summon_pilgrim(enemy)
                    return
                if self.rng.random() < 0.55:
                    self.player.bleed_turns = max(self.player.bleed_turns, 3)
                    self.log("Vaelrith's Blood Pulse leaves you bleeding.")
        elif enemy.kind == EnemyKind.FALSE_PILGRIM and self.rng.random() < 0.25:
            self.player.bleed_turns = max(self.player.bleed_turns, 2)
            self.log("The False Pilgrim leaves a bleeding cut.")
        elif enemy.kind == EnemyKind.OVERSEER and self.rng.random() < 0.35:
            self.player.focus = max(0, self.player.focus - 2)
            self.log("The Overseer's gaze drains 2 focus.")
        raw = enemy.attack + self.rng.randint(-2, 3) - self.player.defense
        damage = max(1, round(raw * multiplier))
        self.player.hp = max(0, self.player.hp - damage)
        self.log(f"{enemy.kind.value} hits you for {damage} damage.")

    def _summon_pilgrim(self, boss: Enemy) -> None:
        candidates = [(boss.x - 1, boss.y), (boss.x + 1, boss.y), (boss.x, boss.y - 1), (boss.x, boss.y + 1)]
        summoned = 0
        for x, y in candidates:
            if self._is_walkable(x, y) and self._enemy_at(x, y) is None and self.player is not None and (x, y) != (self.player.x, self.player.y):
                self.room.enemies.append(make_enemy(EnemyKind.FALSE_PILGRIM, x, y))
                summoned += 1
                if summoned == 2:
                    break
        if summoned == 2:
            self.log("Two False Pilgrims answer Vaelrith's blood call.")
        elif summoned == 1:
            self.log("A False Pilgrim answers Vaelrith's blood call.")

    def _move_enemy(self, enemy: Enemy) -> None:
        if self.player is None:
            return
        options = []
        if self.player.x > enemy.x:
            options.append((enemy.x + 1, enemy.y))
        if self.player.x < enemy.x:
            options.append((enemy.x - 1, enemy.y))
        if self.player.y > enemy.y:
            options.append((enemy.x, enemy.y + 1))
        if self.player.y < enemy.y:
            options.append((enemy.x, enemy.y - 1))
        for x, y in options:
            if self._is_walkable(x, y) and self._enemy_at(x, y) is None and (x, y) != (self.player.x, self.player.y):
                enemy.x, enemy.y = x, y
                return

    def _defeat_enemy(self, enemy: Enemy) -> None:
        if self.player is None:
            return
        self.player.shards += enemy.shards
        self.log(f"{enemy.kind.value} falls. Relic shards +{enemy.shards}.")
        if enemy.boss:
            self.room.cleared = True
            self.mode = "victory"
            self.log("Vaelrith falls. The First Seal breaks, but the temple does not forget.")

    def _defeat(self) -> None:
        self.mode = "defeat"
        self.log("The Blood Wing closes around you.")

    def _nearest_enemy(self, maximum_distance: int) -> Enemy | None:
        if self.player is None:
            return None
        candidates = [enemy for enemy in self.room.living_enemies() if self._distance(self.player.x, self.player.y, enemy.x, enemy.y) <= maximum_distance]
        if not candidates:
            return None
        return min(candidates, key=lambda enemy: self._distance(self.player.x, self.player.y, enemy.x, enemy.y))

    def _enemy_at(self, x: int, y: int) -> Enemy | None:
        for enemy in self.room.living_enemies():
            if enemy.x == x and enemy.y == y:
                return enemy
        return None

    def _inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.room.width and 0 <= y < self.room.height

    def _is_walkable(self, x: int, y: int) -> bool:
        return self._inside(x, y) and self.room.tile_at(x, y) != "#"

    @staticmethod
    def _distance(first_x: int, first_y: int, second_x: int, second_y: int) -> int:
        return abs(first_x - second_x) + abs(first_y - second_y)

    def to_dict(self) -> dict[str, object]:
        if self.player is None:
            raise ValueError("A game must have a player before it can be saved.")
        return {
            "room_index": self.room_index,
            "player": self.player.to_dict(),
            "rooms": [room.to_dict() for room in self.rooms],
            "mode": self.mode,
            "pending_choice": self.pending_choice,
            "events": self.events,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        self.log("The journey has been saved.")

    @classmethod
    def load(cls, path: Path, rng: Random | None = None) -> GameState:
        data = json.loads(path.read_text(encoding="utf-8"))
        state = cls(rng)
        state.room_index = int(data["room_index"])
        state.player = Player.from_dict(dict(data["player"]))
        state.rooms = [RoomState.from_dict(room) for room in list(data["rooms"])]
        state.mode = str(data.get("mode", "playing"))
        pending_choice = data.get("pending_choice")
        state.pending_choice = str(pending_choice) if pending_choice in {"shrine", "shop"} else None
        state.events = [str(event) for event in list(data.get("events", []))][-8:]
        state.log("The Blood Wing remembers where you stopped.")
        return state
