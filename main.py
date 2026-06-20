from __future__ import annotations

import tkinter as tk
from pathlib import Path

from game.engine import GameState
from game.models import HeroClass


TILE_SIZE = 36
MAP_WIDTH = 18
MAP_HEIGHT = 12
CANVAS_WIDTH = TILE_SIZE * MAP_WIDTH
CANVAS_HEIGHT = TILE_SIZE * MAP_HEIGHT
ASSET_DIR = Path(__file__).parent / "assets"


class EthereaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Etherea: Blood Wing")
        self.root.configure(bg="#120f18")
        self.root.resizable(False, False)
        self.fullscreen = False
        self.save_path = Path(__file__).parent / "saves" / "blood_wing_save.json"
        self.state = GameState()
        self.sprite_sources: dict[str, tk.PhotoImage] = {}
        self.sprites: dict[str, tk.PhotoImage] = {}
        self.class_sprites: dict[HeroClass, tk.PhotoImage] = {}
        self.choice_frame: tk.Frame | None = None
        self._load_sprites()

        shell = tk.Frame(root, bg="#120f18", padx=18, pady=18)
        shell.pack()

        self.canvas = tk.Canvas(shell, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="#17131d", highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=2, sticky="n")

        self.sidebar = tk.Frame(shell, width=330, height=CANVAS_HEIGHT, bg="#211a2a", padx=18, pady=18)
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        self.sidebar.grid_propagate(False)

        self.title_var = tk.StringVar(value="TEMPLE OF THE SLEEPERS")
        self.stats_var = tk.StringVar(value="Choose a path to begin.")
        self.objective_var = tk.StringVar(value="The Blood Wing is waiting.")
        self.status_var = tk.StringVar(value="")

        tk.Label(self.sidebar, textvariable=self.title_var, bg="#211a2a", fg="#f2c6d8", font=("Consolas", 13, "bold"), justify="left", anchor="w", wraplength=280).pack(fill="x")
        tk.Label(self.sidebar, textvariable=self.objective_var, bg="#211a2a", fg="#d4adb9", font=("Segoe UI", 9), justify="left", anchor="w", wraplength=285).pack(fill="x", pady=(8, 14))
        tk.Label(self.sidebar, textvariable=self.stats_var, bg="#2a2234", fg="#f8e6ef", font=("Consolas", 9), justify="left", anchor="w", padx=11, pady=10, wraplength=275).pack(fill="x")

        tk.Label(self.sidebar, text="EVENT LOG", bg="#211a2a", fg="#d98ca8", font=("Consolas", 9, "bold"), anchor="w").pack(fill="x", pady=(16, 5))
        self.log_box = tk.Text(self.sidebar, height=10, width=34, bg="#17131d", fg="#e4c7d4", insertbackground="#e4c7d4", relief="flat", wrap="word", font=("Consolas", 8), padx=9, pady=8, state="disabled")
        self.log_box.pack(fill="x")

        self.controls = tk.Label(self.sidebar, text="WASD / Arrows: move\nSpace: attack\nQ: class ability\nE: Blood Vial\nR: recover focus\nB: save   L: load\nF11: fullscreen   Esc: exit", bg="#211a2a", fg="#bba4b3", font=("Consolas", 8), justify="left", anchor="w")
        self.controls.pack(fill="x", pady=(13, 0))

        button_row = tk.Frame(shell, bg="#120f18")
        button_row.grid(row=1, column=1, sticky="ew", padx=(14, 0), pady=(14, 0))
        self.save_button = self._button(button_row, "Save", self.save_game)
        self.load_button = self._button(button_row, "Load", self.load_game)
        self.restart_button = self._button(button_row, "New Run", self.show_class_select)
        self.save_button.pack(side="left", padx=(0, 7))
        self.load_button.pack(side="left", padx=(0, 7))
        self.restart_button.pack(side="left")

        self.class_frame = tk.Frame(self.canvas, bg="#211a2a", padx=22, pady=20)
        self._build_class_select()
        self.canvas.create_window(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2, window=self.class_frame, tags="class_menu")

        self.root.bind_all("<Key>", self.handle_key)
        self.render()

    def _button(self, parent: tk.Widget, text: str, command: object) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg="#6f3152", fg="#fff6f9", activebackground="#9e4c73", activeforeground="#fff6f9", relief="flat", padx=10, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2")

    def _build_class_select(self) -> None:
        tk.Label(self.class_frame, text="ETHEREA", bg="#211a2a", fg="#f0b4cc", font=("Consolas", 22, "bold")).pack()
        tk.Label(self.class_frame, text="Ashes of the Saints\nBlood Wing", bg="#211a2a", fg="#d4adb9", font=("Consolas", 10), justify="center").pack(pady=(5, 15))
        tk.Label(self.class_frame, text="Choose a path", bg="#211a2a", fg="#fff5f9", font=("Segoe UI", 11, "bold")).pack(pady=(0, 10))
        choices = [
            (HeroClass.WARDEN, "Warden", "Balanced guardian · Shield Bash"),
            (HeroClass.ASHEN_BLADE, "Ashen Blade", "High damage · Cinder Arc"),
            (HeroClass.DREAMSEER, "Dreamseer", "Focus magic · Dream Lance"),
        ]
        choice_row = tk.Frame(self.class_frame, bg="#211a2a")
        choice_row.pack()
        for column, (hero_class, title, text) in enumerate(choices):
            button = tk.Button(choice_row, text=f"{title}\n{text}", image=self.class_sprites.get(hero_class), compound="top", command=lambda value=hero_class: self.start_game(value), bg="#3a2639", fg="#ffeaf2", activebackground="#70415d", activeforeground="#ffffff", relief="flat", padx=8, pady=9, width=150, wraplength=140, justify="center", font=("Segoe UI", 9), cursor="hand2")
            button.grid(row=0, column=column, padx=4)

    def _load_sprites(self) -> None:
        files = {
            HeroClass.WARDEN.value: "warden.png",
            HeroClass.ASHEN_BLADE.value: "ashen-blade.png",
            HeroClass.DREAMSEER.value: "dreamseer.png",
            "False Pilgrim": "false-pilgrim.png",
            "Overseer": "overseer.png",
            "Sealbound Knight": "sealbound-knight.png",
            "Bloodbound Pilgrim": "bloodbound-pilgrim.png",
            "Vaelrith": "vaelrith.png",
        }
        for key, filename in files.items():
            path = ASSET_DIR / filename
            if not path.exists():
                continue
            source = tk.PhotoImage(file=str(path))
            self.sprite_sources[key] = source
            self.sprites[key] = source.subsample(3, 3)
        for hero_class in HeroClass:
            source = self.sprite_sources.get(hero_class.value)
            if source is not None:
                self.class_sprites[hero_class] = source.subsample(2, 2)

    def start_game(self, hero_class: HeroClass) -> None:
        self.state.start(hero_class)
        self.canvas.delete("class_menu")
        self.class_frame.place_forget()
        self.render()
        self.canvas.focus_set()

    def show_class_select(self) -> None:
        self.state = GameState()
        self.canvas.delete("all")
        self.class_frame.destroy()
        self.class_frame = tk.Frame(self.canvas, bg="#211a2a", padx=22, pady=20)
        self._build_class_select()
        self.canvas.create_window(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2, window=self.class_frame, tags="class_menu")
        self.render()

    def handle_key(self, event: tk.Event[tk.Misc]) -> None:
        key = event.keysym.lower()
        if key == "f11":
            self.toggle_fullscreen()
            return
        if key == "escape" and self.fullscreen:
            self.toggle_fullscreen()
            return
        if self.state.mode == "class_select":
            choices = {"1": HeroClass.WARDEN, "2": HeroClass.ASHEN_BLADE, "3": HeroClass.DREAMSEER}
            if event.char in choices:
                self.start_game(choices[event.char])
            return
        if self.state.pending_choice == "shrine":
            if event.char == "1":
                self.resolve_choice("health")
            elif event.char == "2":
                self.resolve_choice("focus")
            return
        if self.state.pending_choice == "shop":
            if event.char == "1":
                self.resolve_choice("buy")
            elif event.char == "2":
                self.resolve_choice("leave")
            return
        if key in {"w", "up"}:
            self.state.move(0, -1)
        elif key in {"s", "down"}:
            self.state.move(0, 1)
        elif key in {"a", "left"}:
            self.state.move(-1, 0)
        elif key in {"d", "right"}:
            self.state.move(1, 0)
        elif key == "space":
            self.state.attack()
        elif key == "q":
            self.state.special()
        elif key == "e":
            self.state.use_potion()
        elif key == "r":
            self.state.rest()
        elif key == "b":
            self.save_game()
        elif key == "l":
            self.load_game()
        self.render()

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def resolve_choice(self, choice: str) -> None:
        if self.state.pending_choice == "shrine":
            self.state.choose_shrine(choice)
        elif self.state.pending_choice == "shop":
            self.state.choose_shop(choice)
        self.render()
        self.canvas.focus_set()

    def save_game(self) -> None:
        if self.state.player is None or self.state.mode not in {"playing", "victory", "defeat"}:
            return
        self.state.save(self.save_path)
        self.render()

    def load_game(self) -> None:
        if not self.save_path.exists():
            self.state.log("No saved Blood Wing run was found.")
            self.render()
            return
        try:
            self.state = GameState.load(self.save_path)
            self.canvas.delete("class_menu")
        except (OSError, ValueError, KeyError) as error:
            self.state.log(f"The save could not be read: {error}")
        self.render()
        self.canvas.focus_set()

    def render(self) -> None:
        self.canvas.delete("map")
        self._clear_choice_prompt()
        if self.state.player is None:
            self._draw_menu_background()
            self._update_sidebar()
            return
        self._draw_map()
        self._update_sidebar()
        self._draw_choice_prompt()
        if self.state.mode in {"victory", "defeat"}:
            self._draw_end_overlay()

    def _draw_menu_background(self) -> None:
        self.canvas.create_rectangle(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, fill="#17131d", outline="", tags="map")
        for x in range(0, CANVAS_WIDTH, TILE_SIZE):
            for y in range(0, CANVAS_HEIGHT, TILE_SIZE):
                color = "#211a2a" if (x // TILE_SIZE + y // TILE_SIZE) % 2 == 0 else "#1c1623"
                self.canvas.create_rectangle(x, y, x + TILE_SIZE, y + TILE_SIZE, fill=color, outline="#2a2031", tags="map")

    def _draw_map(self) -> None:
        room = self.state.room
        colors = {"#": "#17151d", ".": "#34293b", "~": "#6d1f3b", "!": "#a57427", "†": "#6d4a8d", ">": "#b8943a"}
        for y, row in enumerate(room.tiles):
            for x, tile in enumerate(row):
                left = x * TILE_SIZE
                top = y * TILE_SIZE
                color = colors.get(tile, "#34293b")
                self.canvas.create_rectangle(left, top, left + TILE_SIZE, top + TILE_SIZE, fill=color, outline="#241d2b", tags="map")
                if tile == "#":
                    self.canvas.create_rectangle(left + 5, top + 6, left + TILE_SIZE - 5, top + TILE_SIZE - 7, outline="#4a3e53", tags="map")
                elif tile == "~":
                    self.canvas.create_line(left + 7, top + 10, left + TILE_SIZE - 8, top + TILE_SIZE - 10, fill="#b6495d", width=2, tags="map")
                elif tile == "!":
                    self.canvas.create_rectangle(left + 10, top + 12, left + 26, top + 26, fill="#ebc260", outline="#fff0a8", tags="map")
                elif tile == "†":
                    self.canvas.create_line(left + 18, top + 7, left + 18, top + 29, fill="#e9c7ff", width=3, tags="map")
                    self.canvas.create_line(left + 11, top + 14, left + 25, top + 14, fill="#e9c7ff", width=3, tags="map")
                elif tile == ">":
                    self.canvas.create_polygon(left + 10, top + 7, left + 28, top + 18, left + 10, top + 29, fill="#f1d374", outline="#fff3b5", tags="map")

        for enemy in room.living_enemies():
            self._draw_actor(enemy.x, enemy.y, enemy.kind.value, enemy.color, enemy.glyph, enemy.boss)
        player = self.state.player
        self._draw_actor(player.x, player.y, player.hero_class.value, "#fff1f6", "@", False, outline="#c87498")
        if any(enemy.boss for enemy in room.living_enemies()):
            boss = next(enemy for enemy in room.living_enemies() if enemy.boss)
            self._draw_boss_bar(boss)

    def _draw_actor(self, x: int, y: int, sprite_key: str, color: str, glyph: str, boss: bool, outline: str = "#120f18") -> None:
        image = self.sprites.get(sprite_key)
        if image is not None:
            self.canvas.create_image(x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2, image=image, tags="map")
            return
        left = x * TILE_SIZE + 6
        top = y * TILE_SIZE + 6
        inset = 2 if boss else 5
        self.canvas.create_rectangle(left - inset, top - inset, left + TILE_SIZE - 12 + inset, top + TILE_SIZE - 12 + inset, fill=color, outline=outline, width=2, tags="map")
        self.canvas.create_text(x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2, text=glyph, fill="#1b1420", font=("Consolas", 12 if boss else 10, "bold"), tags="map")

    def _draw_boss_bar(self, boss: object) -> None:
        left = 130
        top = 12
        width = 380
        health = boss.hp / boss.max_hp
        self.canvas.create_rectangle(left, top, left + width, top + 15, fill="#341423", outline="#ef97ad", tags="map")
        self.canvas.create_rectangle(left, top, left + width * health, top + 15, fill="#d61f48", outline="", tags="map")
        self.canvas.create_text(CANVAS_WIDTH // 2, top + 28, text="VAELRITH, HERALD OF THE FIRST SEAL", fill="#ffd5df", font=("Consolas", 9, "bold"), tags="map")

    def _update_sidebar(self) -> None:
        if self.state.player is None:
            self.title_var.set("TEMPLE OF THE SLEEPERS")
            self.objective_var.set("Choose a class, then enter the Blood Wing.")
            self.stats_var.set("Warden: defense\nAshen Blade: attack\nDreamseer: focus magic")
            self._set_log(["Etherea: Ashes of the Saints", "A small Tkinter dungeon prototype."])
            return
        player = self.state.player
        effects = []
        if player.bleed_turns:
            effects.append(f"Bleeding {player.bleed_turns}")
        if player.empowered_turns:
            effects.append(f"Empowered {player.empowered_turns}")
        effect_text = ", ".join(effects) if effects else "None"
        self.title_var.set(f"{self.state.room.name}\n{self.state.room.subtitle}")
        self.objective_var.set(self.state.objective())
        self.stats_var.set(
            f"{player.hero_class.value}\n\nHP  {player.hp}/{player.max_hp}\nFocus  {player.focus}/{player.max_focus}\n"
            f"Attack  {player.attack_value()}\nDefense  {player.defense}\nBlood Vials  {player.potions}\nRelic Shards  {player.shards}\nEffects  {effect_text}"
        )
        self._set_log(self.state.events)

    def _set_log(self, events: list[str]) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.insert("1.0", "\n\n".join(events[-5:]))
        self.log_box.configure(state="disabled")

    def _draw_end_overlay(self) -> None:
        text = "THE FIRST SEAL BREAKS" if self.state.mode == "victory" else "THE BLOOD WING KEEPS YOU"
        color = "#f0b4cc" if self.state.mode == "victory" else "#f17894"
        self.canvas.create_rectangle(65, 150, CANVAS_WIDTH - 65, 280, fill="#17131d", outline=color, width=2, tags="map")
        self.canvas.create_text(CANVAS_WIDTH // 2, 195, text=text, fill=color, font=("Consolas", 16, "bold"), tags="map")
        self.canvas.create_text(CANVAS_WIDTH // 2, 232, text="Choose New Run to begin again.", fill="#e8c7d5", font=("Segoe UI", 10), tags="map")

    def _clear_choice_prompt(self) -> None:
        if self.choice_frame is not None:
            self.choice_frame.destroy()
            self.choice_frame = None

    def _draw_choice_prompt(self) -> None:
        if self.state.pending_choice not in {"shrine", "shop"}:
            return
        self.choice_frame = tk.Frame(self.canvas, bg="#211a2a", padx=18, pady=14, highlightbackground="#c87498", highlightthickness=2)
        if self.state.pending_choice == "shrine":
            title = "SAINT SHRINE"
            body = "Choose what the shrine should restore."
            options = [("1 · Restore 16 HP", "health"), ("2 · Restore 6 focus + Blood Vial", "focus")]
        else:
            title = "RELIQUARY MERCHANT"
            body = "Spend 30 relic shards for one Blood Vial?"
            options = [("1 · Buy Blood Vial", "buy"), ("2 · Keep shards and continue", "leave")]
        tk.Label(self.choice_frame, text=title, bg="#211a2a", fg="#f0b4cc", font=("Consolas", 11, "bold")).pack()
        tk.Label(self.choice_frame, text=body, bg="#211a2a", fg="#e4c7d4", font=("Segoe UI", 9)).pack(pady=(5, 9))
        for label, choice in options:
            button = tk.Button(self.choice_frame, text=label, command=lambda value=choice: self.resolve_choice(value), bg="#6f3152", fg="#fff6f9", activebackground="#9e4c73", activeforeground="#fff6f9", relief="flat", padx=10, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2")
            button.pack(fill="x", pady=3)
        self.canvas.create_window(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2, window=self.choice_frame, tags="choice_prompt")


def main() -> None:
    root = tk.Tk()
    EthereaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
