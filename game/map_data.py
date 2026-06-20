from __future__ import annotations

from game.models import Enemy, EnemyKind, RoomState


ENEMY_MARKERS: dict[str, EnemyKind] = {
    "E": EnemyKind.FALSE_PILGRIM,
    "O": EnemyKind.OVERSEER,
    "K": EnemyKind.SEALBOUND_KNIGHT,
    "B": EnemyKind.BLOODBOUND_PILGRIM,
    "V": EnemyKind.VAELRITH,
}


def make_enemy(kind: EnemyKind, x: int, y: int) -> Enemy:
    values = {
        EnemyKind.FALSE_PILGRIM: (25, 7, 1, 8, "P", "#c85e68"),
        EnemyKind.OVERSEER: (22, 8, 0, 10, "O", "#70c7d4"),
        EnemyKind.SEALBOUND_KNIGHT: (42, 10, 4, 17, "K", "#aeb4c4"),
        EnemyKind.BLOODBOUND_PILGRIM: (34, 11, 2, 15, "B", "#a93b55"),
        EnemyKind.VAELRITH: (125, 16, 5, 120, "V", "#d61f48"),
    }
    hp, attack, defense, shards, glyph, color = values[kind]
    return Enemy(kind, x, y, hp, hp, attack, defense, shards, glyph, color)


ROOMS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "Blood-Worn Entrance",
        "The first stones of the Blood Wing remember every pilgrim who turned back too late.",
        (
            "##################",
            "#@....†..........#",
            "#....####........#",
            "#...........~....#",
            "#..E.............#",
            "#.......!........#",
            "#................#",
            "#.....####.......#",
            "#............E...#",
            "#..............>.#",
            "#................#",
            "##################",
        ),
    ),
    (
        "Hall of Sleeping Chains",
        "The chains do not move, but their shadows reach for the floor beneath your feet.",
        (
            "##################",
            "#@...............#",
            "#.######.........#",
            "#......#....O....#",
            "#.~~...#.........#",
            "#......#####.....#",
            "#..†.............#",
            "#..........K.....#",
            "#....######......#",
            "#..............>.#",
            "#................#",
            "##################",
        ),
    ),
    (
        "Ritual Combat Chamber",
        "A red seal has been carved into the floor. The old ritual still expects an answer.",
        (
            "##################",
            "#@...............#",
            "#....####........#",
            "#....#..#....B...#",
            "#....#..#........#",
            "#...........~....#",
            "#.######.........#",
            "#...........O....#",
            "#....!...........#",
            "#..............>.#",
            "#................#",
            "##################",
        ),
    ),
    (
        "First Seal Arena",
        "The seal opens like an eye. Vaelrith has been waiting beneath it.",
        (
            "##################",
            "#@...............#",
            "#................#",
            "#....~~~~~~~~....#",
            "#....~......~....#",
            "#....~..V...~....#",
            "#....~......~....#",
            "#....~~~~~~~~....#",
            "#................#",
            "#.......†........#",
            "#................#",
            "##################",
        ),
    ),
]


def build_rooms() -> list[RoomState]:
    rooms = []
    for name, subtitle, rows in ROOMS:
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError(f"Room layout for {name} is not rectangular.")
        start = (1, 1)
        tiles: list[list[str]] = []
        enemies: list[Enemy] = []
        for y, row in enumerate(rows):
            tile_row = []
            for x, tile in enumerate(row):
                if tile == "@":
                    start = (x, y)
                    tile_row.append(".")
                elif tile in ENEMY_MARKERS:
                    enemies.append(make_enemy(ENEMY_MARKERS[tile], x, y))
                    tile_row.append(".")
                else:
                    tile_row.append(tile)
            tiles.append(tile_row)
        rooms.append(RoomState(name, subtitle, tiles, start, enemies))
    return rooms
