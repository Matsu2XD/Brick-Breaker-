"""Tela inicial, ajustes, placar de lideres, persistencia e trilha sonora."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from src import audio as audio_module
from src import config, store
from src.audio import SoundBank, is_music
from src.controls import InputState
from src.game import Game, State
from src.menu import ITEMS, Kind, Menu, Screen
from src.modifiers import specs
from src.scores import Leaderboard, ScoreEntry
from src.settings import Settings
from tests.harness import check, finish

# O harness ja apontou SAVE_DIR para um diretorio temporario; este teste escreve
# bastante, entao confirma que o isolamento esta de pe.
TEMP_SAVE = config.SAVE_DIR


def menu_key(game, key):
    game._handle_keydown(key)


check("the tests write to a throwaway save directory, not the player's",
      "brickbreaker-test-" in TEMP_SAVE and os.path.isdir(TEMP_SAVE),
      TEMP_SAVE)


# ========================================================== persistencia ====
check("a missing file falls back to the defaults",
      store.load("nao_existe.json", {"a": 1}) == {"a": 1})
check("saving creates the directory and the file",
      store.save("sample.json", {"a": 2})
      and os.path.isfile(os.path.join(TEMP_SAVE, "sample.json")))
check("a saved file comes back the same",
      store.load("sample.json", {"a": 1})["a"] == 2,
      f"{store.load('sample.json', {'a': 1})}")
check("a missing key is filled from the defaults",
      store.load("sample.json", {"a": 1, "b": 9}).get("b") == 9)

with open(os.path.join(TEMP_SAVE, "broken.json"), "w", encoding="utf-8") as handle:
    handle.write("{ isto nao e json")
check("a corrupt file falls back instead of raising",
      store.load("broken.json", {"ok": True}) == {"ok": True})

with open(os.path.join(TEMP_SAVE, "list.json"), "w", encoding="utf-8") as handle:
    handle.write("[1, 2, 3]")
check("a json that is not an object falls back",
      store.load("list.json", {"ok": True}) == {"ok": True})

# ============================================================== ajustes ====
settings = Settings()
check("the defaults are sane",
      settings.music_enabled and settings.sfx_enabled and settings.particles
      and settings.screen_shake and 0.0 < settings.sfx_volume <= 1.0
      and 0.0 < settings.music_volume <= 1.0,
      f"{settings}")
check("settings save and load round-trip",
      settings.save() and Settings.load().sfx_volume == settings.sfx_volume)

settings.music_enabled = False
settings.sfx_volume = 0.25
settings.particles = False
settings.save()
reloaded = Settings.load()
check("every field survives a round-trip",
      not reloaded.music_enabled and reloaded.sfx_volume == 0.25
      and not reloaded.particles and reloaded.screen_shake,
      f"{reloaded}")

store.save(config.SETTINGS_FILE, {
    "music_enabled": "sim", "sfx_volume": 99, "particles": 3, "screen_shake": None,
})
repaired = Settings.load()
check("a hand-edited file cannot break the game",
      isinstance(repaired.music_enabled, bool) and repaired.music_enabled
      and repaired.sfx_volume == 1.0 and isinstance(repaired.particles, bool)
      and repaired.screen_shake is True,
      f"{repaired}")

repaired.reset()
check("reset puts every field back to the default",
      repaired.sfx_volume == Settings().sfx_volume
      and repaired.particles == Settings().particles)

# =============================================================== placar ====
board = Leaderboard(entries=[])
check("an empty board has no best score", board.best == 0)
check("zero does not qualify", not board.qualifies(0))
check("a positive score qualifies on an empty board", board.qualifies(500))
check("submitting returns the position", board.submit(500, 2, "2026-01-01") == 1)
check("a better score takes the top", board.submit(900, 4, "2026-01-02") == 1)
check("a worse score goes to the bottom", board.submit(100, 1, "2026-01-03") == 3)
check("the board lists best first",
      [entry.score for entry in board.entries] == [900, 500, 100],
      f"{[entry.score for entry in board.entries]}")
check("the best is the first entry", board.best == 900)

reloaded_board = Leaderboard.load()
check("the board survives a reload",
      [entry.score for entry in reloaded_board.entries] == [900, 500, 100],
      f"{[entry.score for entry in reloaded_board.entries]}")
check("the level travelled with the score", reloaded_board.entries[0].level == 4)

full = Leaderboard(entries=[])
for index in range(config.SCORES_KEPT):
    full.submit(100 + index, 1, "2026-01-01")
check("the board is capped", len(full.entries) == config.SCORES_KEPT,
      f"{len(full.entries)}")
check("a score below the cut does not qualify", not full.qualifies(50))
check("a weak score at the cap is rejected", full.submit(1, 1) == 0)
check("a strong score at the cap still enters", full.submit(9999, 9) == 1)
check("the cap is kept after inserting", len(full.entries) == config.SCORES_KEPT)

check("a malformed entry is dropped on load",
      ScoreEntry.from_raw({"score": "muitos"}) is None
      and ScoreEntry.from_raw("nada") is None
      and ScoreEntry.from_raw({"score": -5}) is None)
check("a valid entry loads", ScoreEntry.from_raw({"score": 10, "level": 3}) is not None)
check("a missing level becomes 1",
      ScoreEntry.from_raw({"score": 10}).level == 1)

store.save(config.SCORES_FILE, {"scores": [{"score": "x"}, {"score": 7}, None]})
salvaged = Leaderboard.load()
check("a corrupt board keeps whatever was readable",
      [entry.score for entry in salvaged.entries] == [7],
      f"{[entry.score for entry in salvaged.entries]}")

# ================================================================= menu =====
clean = Settings()
menu = Menu(settings=clean)
check("the menu opens on the main screen", menu.screen is Screen.MAIN)
check("the main screen lists the expected actions",
      [item.action for item in ITEMS[Screen.MAIN]]
      == ["play", "scores", "settings", "quit"])
check("the cursor starts at the top", menu.cursor == 0)

menu.move(1)
check("down moves the cursor", menu.cursor == 1)
menu.move(-1)
menu.move(-1)
check("up wraps around the list", menu.cursor == len(ITEMS[Screen.MAIN]) - 1,
      f"{menu.cursor}")
menu.move(1)
check("down also wraps", menu.cursor == 0)

menu.open(Screen.SETTINGS)
check("opening a screen moves the cursor to the top", menu.cursor == 0)
check("opening records where it came from", menu.return_to is Screen.MAIN)
settings_item = menu.current
check("the first setting is the music switch",
      settings_item.setting == "music_enabled" and settings_item.kind is Kind.TOGGLE,
      f"{settings_item}")
check("a toggle shows its state", menu.value_text(settings_item) in ("LIGADO", "DESLIGADO"),
      f"{menu.value_text(settings_item)}")

before = clean.music_enabled
menu.adjust(1)
check("left/right flips a toggle", clean.music_enabled is not before)
menu.activate()
check("enter also flips a toggle", clean.music_enabled is before)

menu.move(1)
volume_item = menu.current
check("the second setting is the music volume",
      volume_item.setting == "music_volume" and volume_item.kind is Kind.SLIDER)
clean.music_volume = 0.5
menu.adjust(-1)
check("a slider steps down", abs(clean.music_volume - 0.4) < 1e-9, f"{clean.music_volume}")
menu.adjust(1)
check("a slider steps back up", abs(clean.music_volume - 0.5) < 1e-9)
for _ in range(20):
    menu.adjust(1)
check("a slider clamps at the top", clean.music_volume == 1.0, f"{clean.music_volume}")
for _ in range(20):
    menu.adjust(-1)
check("a slider clamps at the bottom", clean.music_volume == 0.0, f"{clean.music_volume}")
check("a slider shows a percentage", menu.value_text(volume_item) == "0%",
      f"{menu.value_text(volume_item)}")

menu.cursor = len(ITEMS[Screen.SETTINGS]) - 1
check("the last settings item is the way back", menu.current.action == "back")
check("activate only reports the intent, without navigating",
      menu.activate() == "back" and menu.screen is Screen.SETTINGS)
menu.back()
check("back returns to where it came from", menu.screen is Screen.MAIN)

menu.open(Screen.PAUSED)
menu.open(Screen.SETTINGS)
menu.back()
check("back from the pause settings returns to the pause menu",
      menu.screen is Screen.PAUSED)
check("the pause menu has no items on the scores screen",
      ITEMS[Screen.SCORES] == ())

# ================================================================= trilha ===
check("the music prefix rule recognises the track",
      is_music("background_music_01") and not is_music("ball_sound"),
      f"{is_music('background_music_01')}")

game = Game(seed=1)
check("the sound bank found the music file", game.audio.music_available,
      f"{game.audio.music_path}")
check("the music file is not also loaded as an effect",
      "background_music_01" not in game.audio.library,
      f"{sorted(game.audio.library)}")
no_track = SoundBank()
no_track.music_path = None
check("a bank with no track reports no music, instead of pretending",
      not no_track.music_available and not no_track.start_music())
check("music starts", game.audio.start_music())
check("starting the music twice does not restart it", game.audio.start_music())
game.audio.set_music_level(0.2)
check("the music volume is applied", abs(game.audio.music_level - 0.2) < 1e-9)
game.audio.set_music_enabled(False)
check("turning the music off stops it", not game.audio.music_on)
game.audio.set_music_enabled(True)
check("turning it back on resumes", game.audio.music_on)
check("the quick mute also pauses the music", game.audio.toggle_mute() is True)
game.audio.toggle_mute()
check("unmuting brings it back", game.audio.muted is False)

game.audio.set_sfx_level(0.3)
check("the sfx volume is applied", abs(game.audio.volume - 0.3) < 1e-9)
applied = game.audio.channels["brick"].get_volume()
expected = audio_module.EVENT_VOLUME["brick"]
check("the per-event balance rides on the channel, so shared samples keep theirs",
      abs(applied - expected) < 0.02, f"{applied:.4f} vs {expected:.4f}")
wave_balance = game.audio.channels["wall"].get_volume()
check("two events sharing one file keep different balances",
      abs(wave_balance - audio_module.EVENT_VOLUME["wall"]) < 0.02
      and abs(wave_balance - applied) > 0.05,
      f"parede {wave_balance:.3f} vs tijolo {applied:.3f}")
ball = game.audio.sounds["brick"]
check("every event that shares the file points at the same Sound object",
      game.audio.sounds["wall"] is ball and game.audio.sounds["shoot"] is ball)
game.audio.set_sfx_enabled(False)
check("a disabled bank refuses to play", game.audio.play("brick") is False)
game.audio.set_sfx_enabled(True)
game.shutdown()

# ====================================================== o jogo com menus ====
game = Game(seed=2)
check("the game opens on the menu, not in a match", game.state is State.MENU)
check("a level is ready behind the menu", len(game.bricks) == 77)
check("the menu screen is the main one", game.menu.screen is Screen.MAIN)

menu_key(game, pygame.K_DOWN)
check("the menu cursor moves with S as well as with the arrow",
      game.menu.cursor == 1)

game.menu.cursor = 0
menu_key(game, pygame.K_RETURN)
check("JOGAR starts a match", game.state is State.PLAYING)
check("a fresh match has a fresh score",
      game.score == 0 and game.lives == config.START_LIVES)

menu_key(game, pygame.K_ESCAPE)
check("ESC during a match pauses instead of quitting",
      game.state is State.PAUSED and game.running)
check("the pause menu opens on the pause screen", game.menu.screen is Screen.PAUSED)

game.menu.cursor = 0
menu_key(game, pygame.K_RETURN)
check("CONTINUAR resumes", game.state is State.PLAYING)

menu_key(game, pygame.K_ESCAPE)
game.menu.cursor = 2
menu_key(game, pygame.K_RETURN)
check("RECOMECAR restarts the match", game.state is State.PLAYING and game.score == 0)

menu_key(game, pygame.K_ESCAPE)
game.menu.cursor = 3
menu_key(game, pygame.K_RETURN)
check("ABANDONAR goes back to the menu", game.state is State.MENU)
check("abandoning leaves the main menu on screen", game.menu.screen is Screen.MAIN)

game.menu.cursor = 1
menu_key(game, pygame.K_RETURN)
check("PLACAR opens the scoreboard", game.menu.screen is Screen.SCORES)
menu_key(game, pygame.K_ESCAPE)
check("ESC closes the scoreboard", game.menu.screen is Screen.MAIN)

game.menu.cursor = 2
menu_key(game, pygame.K_RETURN)
check("AJUSTES opens the settings", game.menu.screen is Screen.SETTINGS)
game.menu.cursor = 0
before = game.settings.music_enabled
menu_key(game, pygame.K_RIGHT)
check("changing a setting in the game takes effect at once",
      game.settings.music_enabled is not before
      and game.audio.music_on is game.settings.music_enabled)
menu_key(game, pygame.K_ESCAPE)
check("leaving the settings writes them to disk",
      Settings.load().music_enabled == game.settings.music_enabled)
check("leaving puts the menu back on the main screen", game.menu.screen is Screen.MAIN)
game.shutdown()

# ==================================================== ajustes valendo =======
game = Game(seed=3)
game.settings.particles = False
game.settings.screen_shake = False
menu_key(game, pygame.K_RETURN)
game._handle_launch_key()
game.advance(1 / 60, InputState())
victim = next(b for b in game.bricks if b.alive and b.max_hp == 1)
game._damage_brick(victim)
check("turning particles off really stops the particles", len(game.vfx) == 0,
      f"{len(game.vfx)}")
check("turning shake off really stops the shake", game.shake == 0.0, f"{game.shake}")

game.settings.particles = True
game.settings.screen_shake = True
game._damage_brick(next(b for b in game.bricks if b.alive and b.max_hp == 1))
check("turning them back on brings them back",
      len(game.vfx) > 0 and game.shake > 0.0, f"{len(game.vfx)}/{game.shake}")

game.settings.debug_keys = False
game._debug_spawn(specs.BY_ID["gun"])
check("a disabled debug flag does not disable the method, only the key",
      len(game.capsules) > 0)
game._debug_clear()
game.shutdown()

# ==================================================== fim de jogo e placar ==
game = Game(seed=4)
game.leaderboard.entries.clear()
menu_key(game, pygame.K_RETURN)
game.score = 4321
game.level = 3
game.lives = 1
game.balls = []
game._lose_life()
check("game over is reached", game.state is State.GAME_OVER)
check("the score was recorded", game._final_position == 1, f"{game._final_position}")
check("the recorded score is the one played",
      game.leaderboard.best == 4321, f"{game.leaderboard.best}")
check("the record is on disk",
      Leaderboard.load().best == 4321, f"{Leaderboard.load().best}")

game.draw()
check("the game over screen still draws with a leaderboard on it",
      game.state is State.GAME_OVER)

menu_key(game, pygame.K_ESCAPE)
check("ESC after game over returns to the menu", game.state is State.MENU)
check("the next match starts clean", game.score == 0 and game._final_position == 0)
game.shutdown()

# ============================================================== desenho =====
game = Game(seed=5)
for screen in (Screen.MAIN, Screen.SETTINGS, Screen.SCORES):
    game.menu.screen = screen
    game.draw()
    check(f"the {screen.value} screen renders", True)
game.menu.screen = Screen.PAUSED
game.state = State.PAUSED
game.draw()
check("the pause screen renders", True)

# ---- o texto das telas cabe onde foi posto ---------------------------------
width = config.WINDOW_WIDTH

# menu inicial: itens a esquerda, recordes a direita
menu_centre = width // 4 + 40
side_centre = width // 4 * 3 + 40
side_left = side_centre - 90
widest_item = max(game.font_hud.size(item.label)[0]
                  for item in ITEMS[Screen.MAIN])
widest_record = max(
    (game.font_small.size(f"{index + 1}. {entry.score:>6}  fase {entry.level}")[0]
     for index, entry in enumerate(game.leaderboard.entries[:5])),
    default=0,
)
check("the menu items end before the record column starts",
      menu_centre - 128 + widest_item < side_left,
      f"itens ate {menu_centre - 128 + widest_item}, recordes começam em {side_left}")
check("the record column fits inside the window",
      side_left + widest_record < width - 16,
      f"{side_left + widest_record} vs {width - 16}")

# ajustes: rotulo a esquerda, valor a direita
settings_centre = width // 2
label_right = settings_centre - 128 + max(
    game.font_hud.size(item.label)[0] for item in ITEMS[Screen.SETTINGS])
check("no settings label runs into its value column",
      label_right < settings_centre + 70,
      f"rotulos ate {label_right}, valores a partir de {settings_centre + 70}")
check("the value column stays on screen",
      settings_centre + 70 + game.font_hud.size("DESLIGADO")[0] < width - 16)

# placar: posicao, pontos e data, nesta ordem
check("the scoreboard columns do not collide",
      settings_centre - 210 + game.font_hud.size("99.")[0] < settings_centre - 170
      and settings_centre - 170 + game.font_hud.size("  99999")[0] < settings_centre + 30,
      "posicao / pontos / data")
check("every menu item label is non-empty",
      all(item.label for screen in ITEMS for item in ITEMS[screen]))

game.shutdown()

sys.exit(finish("interface, ajustes, placar e trilha"))
