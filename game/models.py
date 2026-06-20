from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HeroClass(str, Enum):
    WARDEN = "Warden"
    ASHEN_BLADE = "Ashen Blade"
    DREAMSEER = "Dreamseer"


class EnemyKind(str, Enum):
    FALSE_PILGRIM = "False Pilgrim"
    OVERSEER = "Overseer"
    SEALBOUND_KNIGHT = "Sealbound Knight"
    BLOODBOUND_PILGRIM = "Bloodbound Pilgrim"
    VAELRITH = "Vaelrith"


@dataclass
class Player:
    hero_class: HeroClass
    x: int
    y: int
    max_hp: int
    hp: int
    attack: int
    defense: int
    max_focus: int
    focus: int
    shards: int = 0
    potions: int = 2
    bleed_turns: int = 0
    empowered_turns: int = 0

    @classmethod
    def create(cls, hero_class: HeroClass, x: int, y: int) -> Player:
        values = {
            HeroClass.WARDEN: (58, 10, 4, 7),
            HeroClass.ASHEN_BLADE: (46, 14, 2, 8),
            HeroClass.DREAMSEER: (39, 9, 2, 13),
        }
        max_hp, attack, defense, max_focus = values[hero_class]
        return cls(hero_class, x, y, max_hp, max_hp, attack, defense, max_focus, max_focus)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def attack_value(self) -> int:
        return self.attack + (3 if self.empowered_turns > 0 else 0)

    def to_dict(self) -> dict[str, object]:
        return {
            "hero_class": self.hero_class.value,
            "x": self.x,
            "y": self.y,
            "max_hp": self.max_hp,
            "hp": self.hp,
            "attack": self.attack,
            "defense": self.defense,
            "max_focus": self.max_focus,
            "focus": self.focus,
            "shards": self.shards,
            "potions": self.potions,
            "bleed_turns": self.bleed_turns,
            "empowered_turns": self.empowered_turns,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Player:
        return cls(
            hero_class=HeroClass(str(data["hero_class"])),
            x=int(data["x"]),
            y=int(data["y"]),
            max_hp=int(data["max_hp"]),
            hp=int(data["hp"]),
            attack=int(data["attack"]),
            defense=int(data["defense"]),
            max_focus=int(data["max_focus"]),
            focus=int(data["focus"]),
            shards=int(data["shards"]),
            potions=int(data["potions"]),
            bleed_turns=int(data.get("bleed_turns", 0)),
            empowered_turns=int(data.get("empowered_turns", 0)),
        )


@dataclass
class Enemy:
    kind: EnemyKind
    x: int
    y: int
    max_hp: int
    hp: int
    attack: int
    defense: int
    shards: int
    glyph: str
    color: str
    stun_turns: int = 0
    bleed_turns: int = 0
    phase_announced: int = 1
    summoned: bool = False

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def boss(self) -> bool:
        return self.kind == EnemyKind.VAELRITH

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "x": self.x,
            "y": self.y,
            "max_hp": self.max_hp,
            "hp": self.hp,
            "attack": self.attack,
            "defense": self.defense,
            "shards": self.shards,
            "glyph": self.glyph,
            "color": self.color,
            "stun_turns": self.stun_turns,
            "bleed_turns": self.bleed_turns,
            "phase_announced": self.phase_announced,
            "summoned": self.summoned,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Enemy:
        return cls(
            kind=EnemyKind(str(data["kind"])),
            x=int(data["x"]),
            y=int(data["y"]),
            max_hp=int(data["max_hp"]),
            hp=int(data["hp"]),
            attack=int(data["attack"]),
            defense=int(data["defense"]),
            shards=int(data["shards"]),
            glyph=str(data["glyph"]),
            color=str(data["color"]),
            stun_turns=int(data.get("stun_turns", 0)),
            bleed_turns=int(data.get("bleed_turns", 0)),
            phase_announced=int(data.get("phase_announced", 1)),
            summoned=bool(data.get("summoned", False)),
        )


@dataclass
class RoomState:
    name: str
    subtitle: str
    tiles: list[list[str]]
    start: tuple[int, int]
    enemies: list[Enemy] = field(default_factory=list)
    cleared: bool = False
    lore_seen: bool = False

    @property
    def width(self) -> int:
        return len(self.tiles[0])

    @property
    def height(self) -> int:
        return len(self.tiles)

    def tile_at(self, x: int, y: int) -> str:
        return self.tiles[y][x]

    def set_tile(self, x: int, y: int, value: str) -> None:
        self.tiles[y][x] = value

    def living_enemies(self) -> list[Enemy]:
        return [enemy for enemy in self.enemies if enemy.alive]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "subtitle": self.subtitle,
            "tiles": ["".join(row) for row in self.tiles],
            "start": list(self.start),
            "enemies": [enemy.to_dict() for enemy in self.enemies],
            "cleared": self.cleared,
            "lore_seen": self.lore_seen,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RoomState:
        return cls(
            name=str(data["name"]),
            subtitle=str(data["subtitle"]),
            tiles=[list(str(row)) for row in list(data["tiles"])],
            start=tuple(int(value) for value in list(data["start"])),
            enemies=[Enemy.from_dict(item) for item in list(data["enemies"])],
            cleared=bool(data.get("cleared", False)),
            lore_seen=bool(data.get("lore_seen", False)),
        )
