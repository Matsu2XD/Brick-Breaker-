"""Consistencia do GAME_DESIGN.md contra o codigo.

O documento e a fonte da verdade do design, entao ele nao pode mentir sobre os
numeros: cada valor citado aqui e conferido contra config.py, specs.py e audio.py.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import audio as audio_module
from src import config
from src.events import EVENTS as EVENTS_CATALOG
from src.game import State as GameState
from src.level import build_bricks
from src.menu import Screen
from src.modifiers import specs as specs_module
from tests.harness import PROJECT_ROOT, check, finish

DOC_PATH = os.path.join(PROJECT_ROOT, "GAME_DESIGN.md")
with open(DOC_PATH, encoding="utf-8") as handle:
    doc = handle.read()


def quoted(text: str) -> bool:
    return text in doc


# ---- numeros do motor ------------------------------------------------------
pad = config.PLAYFIELD
check("doc quotes the playfield size", quoted(f"{pad.width} × {pad.height} px"),
      f"{pad.width} × {pad.height}")
check("doc quotes the window size", quoted(f"{config.WINDOW_WIDTH} × {config.WINDOW_HEIGHT}"))
check("doc quotes the FPS",
      quoted(f"{config.WINDOW_WIDTH} × {config.WINDOW_HEIGHT} px · {config.FPS} FPS"))
check("doc quotes HUD height", quoted(f"| HUD | {config.HUD_HEIGHT} px"))
check("doc quotes wall thickness", quoted(f"| Parede | {config.WALL_THICKNESS} px"))
check("doc quotes paddle box",
      quoted(f"{int(config.PADDLE_WIDTH)} × {int(config.PADDLE_HEIGHT)} px"))
check("doc quotes paddle speed", quoted(f"{int(config.PADDLE_SPEED)} px/s"))
check("doc quotes paddle margin", quoted(f"{int(config.PADDLE_BOTTOM_MARGIN)} px do fundo"))
check("doc quotes ball radius", quoted(f"raio {config.BALL_RADIUS:g} px"))
check("doc quotes ball speed", quoted(f"{int(config.BALL_SPEED)} px/s"))
check("doc quotes serve angle", quoted(f"±{config.BALL_SERVE_ANGLE_DEG:g}°"))
check("doc quotes max bounce angle", quoted(f"{config.BALL_MAX_BOUNCE_ANGLE_DEG:g}°"))
check("doc quotes min vertical fraction", quoted(f"{config.BALL_MIN_VERTICAL_FRACTION:g}"))
check("doc quotes precision factor", quoted("0,42"))
check("doc quotes english",
      quoted(f"| `PADDLE_ENGLISH` | {config.PADDLE_ENGLISH:g} |".replace(".", ",")))
check("doc quotes level speed step", quoted("+6 %"))
check("doc quotes lives", quoted(f"| Vidas | {config.START_LIVES} |"))
check("doc quotes fixed timestep", quoted("1/120"))
check("doc quotes max frame time", quoted("0,25 s"))
check("doc quotes substep ratio", quoted("0,5 × raio"))
check("doc quotes collision skin", quoted("0,1 px"))
check("doc quotes paddle max angle table", quoted("−62°") and quoted("+62°"))
check("doc quotes the tunneling scenario", quoted("bola a 60.000 px/s"))

bricks = build_bricks(pad)
check("doc quotes the brick grid", quoted(f"{config.BRICK_ROWS} linhas × {config.BRICK_COLUMNS} colunas"))
check("doc quotes the brick count", quoted("7 × 11 = 77") and len(bricks) == 77,
      f"{len(bricks)} bricks")
check("doc quotes brick height", quoted(f"{config.BRICK_HEIGHT} px de altura"))
check("doc quotes brick gap", quoted(f"vão de {config.BRICK_GAP} px"))
check("doc quotes tough rows", quoted(f"{config.BRICK_TOUGH_ROWS} linhas do topo"))
check("doc quotes score per hit", quoted(f"{config.SCORE_PER_HIT} por acerto"))
check("doc quotes score per brick", quoted(f"{config.SCORE_PER_BRICK} por tijolo"))

# ---- numeros de modificadores ---------------------------------------------
check("doc quotes the ball cap", quoted("| Teto de bolas em jogo | "
                                        f"{config.MAX_BALLS} |"))
check("doc quotes the ball multiplier factors",
      quoted("2 / 4 / 6 / 8") and config.BALL_MULTIPLIER_FACTORS == (2, 4, 6, 8))
check("doc quotes the clone spread", quoted(f"{config.BALL_CLONE_SPREAD_DEG:g}°"))
check("doc quotes the score multiplier ceiling",
      quoted("teto 8x") and config.SCORE_MULTIPLIER_MAX == 8.0)
check("doc quotes the paddle growth",
      quoted(f"×{config.PADDLE_GROW_FACTOR:g} por acúmulo".replace(".", ",")))
check("doc quotes the paddle growth ceiling", quoted("×1,75"))
check("doc quotes the gun magazine", quoted(f"{config.GUN_SHOTS_PER_PICKUP} tiros por coleta"))
check("doc quotes the gun cooldown",
      quoted(f"{config.GUN_COOLDOWN:g} s".replace(".", ",")))
check("doc quotes the projectile speed", quoted(f"{int(config.PROJECTILE_SPEED)} px/s"))
check("doc quotes the fixed-ball speed factor",
      quoted(f"×{config.FAST_BALLS_MULTIPLIER:g}".replace(".", ",")))
check("doc quotes the capsule drop chance",
      quoted(f"{int(config.CAPSULE_DROP_CHANCE * 100)} %"))
check("doc quotes the capsule speed", quoted(f"{int(config.CAPSULE_SPEED)} px/s"))
check("doc quotes the invader speed", quoted(f"{int(config.INVADER_SPEED_Y)} px/s"))

# ---- inferencias ditas em prosa -------------------------------------------
check("doc's level-10 speed claim (+54%) is right",
      quoted("+54 %") and abs(config.LEVEL_SPEED_STEP * 9 - 0.54) < 1e-9)
check("doc's precision speed claim (42%) matches config",
      abs(config.PADDLE_PRECISION_FACTOR - 0.42) < 1e-9)
check("doc's 22% anti-horizontal claim matches config",
      abs(config.BALL_MIN_VERTICAL_FRACTION - 0.22) < 1e-9 and quoted("22 %"))
check("doc's substep size claim (4.5 px) matches config",
      abs(config.BALL_RADIUS * config.MAX_SUBSTEP_RATIO - 4.5) < 1e-9 and quoted("4,5 px"))
check("doc's 120 Hz claim matches timestep",
      abs(config.FIXED_TIMESTEP - 1 / 120) < 1e-12)
check("doc's stacked FAST ceiling is right",
      quoted("×3,42") and abs(config.FAST_BALLS_MULTIPLIER**2 - 3.4225) < 1e-9)
check("doc's fire rate claim is right",
      quoted("4,5 tiros/s") and abs(1 / config.GUN_COOLDOWN - 4.545) < 0.01)
check("doc's effective fast-ball speed claim is right",
      quoted("795 px/s") and abs(config.BALL_SPEED * config.FAST_BALLS_MULTIPLIER - 795.5) < 0.6)

# ---- catalogo --------------------------------------------------------------
MODIFIER_IDS = tuple(spec.id for spec in specs_module.MODIFIERS)
documented = set(re.findall(r"^\| `([a-z_]+)` \|", doc, re.M))
check("doc documents every modifier in the catalogue as a table row",
      set(MODIFIER_IDS) <= documented,
      f"missing: {sorted(set(MODIFIER_IDS) - documented)}")
check("the catalogue has the 4 buffs and 3 debuffs the brief asked for",
      len(MODIFIER_IDS) == 7 and len(specs_module.BUFFS) == 4
      and len(specs_module.DEBUFFS) == 3,
      f"{len(specs_module.BUFFS)} buffs + {len(specs_module.DEBUFFS)} debuffs")
for required in MODIFIER_IDS:
    check(f"catalogue documents {required}", f"| `{required}` |" in doc)

# ---- nomes citados existem no codigo --------------------------------------
# Qualquer rotulo que o codigo saiba desenhar na tela pode aparecer citado no
# documento sem ser constante: nomes de modificador, nomes de chip, nomes de
# evento. Derivar a lista do catalogo evita manter uma lista paralela aqui.
DISPLAY_LABELS = set()
for spec in specs_module.MODIFIERS:
    DISPLAY_LABELS |= {spec.name, spec.short, spec.hud}
for spec in EVENTS_CATALOG:
    DISPLAY_LABELS |= {spec.name, spec.chip}
# Nomes de tela, de estado do jogo e de tecla citados no documento.
DISPLAY_LABELS |= {screen.name for screen in Screen}
DISPLAY_LABELS |= {state.name for state in GameState}
DISPLAY_LABELS.add("ENTER")

NON_CONFIG_TOKENS = {
    "BUFF", "DEBUFF", "PLAYING", "PAUSED", "LEVEL_CLEAR", "GAME_OVER",
    "KEYDOWN", "SDL_VIDEODRIVER", "SDL_AUDIODRIVER", "WASD", "GAME_DESIGN", "ESC",
    "PONTOS", "MUDO", "PATH", "APPDATA", "XDG_DATA_HOME",
} | DISPLAY_LABELS
referenced = set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", doc))
known = {name for name in dir(config) if name.isupper()}
known |= {name for name in dir(audio_module) if name.isupper()}
known |= {name for name in dir(specs_module) if name.isupper()}
unknown = sorted(name for name in referenced
                 if name not in known and name not in NON_CONFIG_TOKENS)
check("doc only references constants and labels that exist in the code", not unknown,
      f"unknown: {unknown}")

# ---- estrutura -------------------------------------------------------------
headings = re.findall(r"^## (\d+)\. (.+)$", doc, re.M)
numbers = [int(number) for number, _ in headings]
check("sections are numbered 1..N without gaps or duplicates",
      numbers == list(range(1, len(numbers) + 1)), f"{numbers}")
check("doc has 23 sections", len(numbers) == 23, f"{len(numbers)} sections")

refs = {int(match) for match in re.findall(r"§(\d+)", doc)}
check("every section cross-reference resolves", refs <= set(numbers),
      f"dangling: {sorted(refs - set(numbers))}")

sub_headings = set(re.findall(r"^### (\d+\.\d+) ", doc, re.M))
sub_refs = set(re.findall(r"§(\d+\.\d+)", doc))
check("every sub-section cross-reference resolves", sub_refs <= sub_headings,
      f"dangling: {sorted(sub_refs - sub_headings)}")
check("sub-references are actually used", len(sub_refs) >= 4, f"{sorted(sub_refs)}")

titles = {int(number): title for number, title in headings}
check("the dynamics section exists", "Dinâmica" in titles[14])
check("the audio section moved to 15", "Áudio" in titles[15])
check("the sprites section is 16 and is referenced from the roadmap",
      "Sprites" in titles[16] and "§16" in doc)
check("the menus section is 17 and is referenced from the roadmap",
      "Menus" in titles[17] and "§17" in doc)
check("the balance table follows the menus", "Balanceamento" in titles[18])
check("the verification section is where §19 points", "Verificação" in titles[19])
check("the road map is where §20 points", "Roadmap" in titles[20])
check("the life-loss rule points at a real sub-section",
      "§11.4" in doc and "### 11.4 Como a morte interage com os efeitos" in doc)
check("the silence fallback points at a real sub-section",
      "§15.5" in doc and "### 15.5 Pendência" in doc)
check("the music sub-section exists", "### 15.6 Trilha sonora" in doc)
check("the leftovers paragraph points at a real sub-section",
      "§14.6" in doc and "### 14.6 O que ficou de fora" in doc)
check("the capsule identity points at the UI section",
      "§16.4" in doc and "### 16.4 Interface" in doc)
check("the test isolation rule points at a real sub-section",
      "§17.6" in doc and "### 17.6 Os testes" in doc)

# ---- menus, ajustes e placar ------------------------------------------------
check("doc lists every menu screen",
      all(f"`{screen.value.upper()}`" in doc or screen.value.upper() in doc
          for screen in Screen))
check("doc documents the save files",
      "save/settings.json" in doc and "save/highscores.json" in doc)
check("doc quotes the leaderboard size",
      quoted(f"| Posições no placar | {config.SCORES_KEPT} |"))
check("doc quotes the default volumes",
      quoted(f"| Volume da música | {int(config.MUSIC_VOLUME * 100)} % (padrão) |")
      and quoted(f"| Volume dos efeitos | {int(config.SOUND_VOLUME * 100)} % (padrão) |"))
check("doc explains the two-level volume bug",
      "canal" in doc and "propriedade do objeto" in doc)
check("doc explains that the pause is a menu, not an overlay",
      "pausa é um menu, não um aviso" in doc)
check("doc records the leaderboard pollution incident",
      "9.035" in doc)
check("doc lists the music prefixes",
      all(prefix in doc for prefix in config.MUSIC_PREFIXES))

# ---- dinamica --------------------------------------------------------------
check("doc documents every event in the catalogue",
      all(f"`{spec.id}`" in doc for spec in EVENTS_CATALOG),
      f"faltando: {[s.id for s in EVENTS_CATALOG if f'`{s.id}`' not in doc]}")
check("doc quotes the event interval",
      quoted(f"{int(config.EVENT_MIN_GAP)} a {int(config.EVENT_MAX_GAP)} segundos"))
check("doc quotes the first event delay",
      quoted(f"primeiro chega aos {int(config.EVENT_FIRST_GAP)} s"))
check("doc quotes the streak reward step",
      quoted(f"**{config.STREAK_REWARD_STEP} tijolos seguidos**"))
check("doc quotes the streak bonus ceiling",
      quoted(f"+{int(config.STREAK_BONUS_STEP * config.STREAK_BONUS_CAP * 100)} %"))
check("doc quotes the clear ramp",
      quoted(f"+{int(config.LEVEL_CLEAR_SPEED_RAMP * 100)} %"))
check("doc quotes the finale trigger",
      quoted(f"**{config.FINALE_BRICKS} tijolos**")
      and quoted(f"**{config.FINALE_BALLS} bolas**"))
check("doc quotes the particle ceiling", quoted(f"**{config.PARTICLE_MAX} partículas**"))
check("doc quotes the particle burst size",
      quoted(f"solta {config.PARTICLE_BRICK_COUNT} fragmentos"))
check("doc quotes the shake magnitudes",
      quoted("1,5 px") and quoted("2,4;") and quoted("9."))
check("doc explains why the shake is not random", quoted("senoides"))
check("doc contrasts events with modifiers",
      quoted("modificador premia, o evento surpreende"))

# ---- sprites ---------------------------------------------------------------
for sprite_range in ("01–20", "21–30", "31–56", "58", "59", "60"):
    check(f"sprite inventory lists {sprite_range}", sprite_range in doc)
check("doc counts the whole atlas", "61 sprites" in doc)
check("doc explains the odd/even brick pair discovery",
      "ímpar inteiro, par rachado" in doc)
check("doc points at the atlas files",
      "Breakout_Tile_Free.png" in doc and "Breakout_Tile_Free.xml" in doc)
check("doc says the game still runs without the sprite pack",
      "`SpriteSheet.available` é falso" in doc)
check("doc explains why the HUD pills were left out",
      "+50" in doc and "1.600" in doc)
check("doc states the worst-case chip measurement",
      "802 px" in doc and "729 px" in doc)
check("doc names the sprites used for the HUD icons",
      "coração" in doc and "estrela" in doc)
check("doc admits there is no paddle sprite", "sprite de bandeja" in doc)

# ---- audio -----------------------------------------------------------------
check("doc lists all four provided sound files",
      all(f"{name}.wav`" in doc for name in ("ball_sound", "power_up_sound",
                                             "lose_ball_sound", "level_complete_sound")))
check("doc documents every audio event that code binds",
      all(f'"{event}"' in doc for event in audio_module.EVENT_SOURCES))
check("doc admits the missing shoot/paddle/debuff sounds",
      "paddle_sound.wav" in doc and "shoot_sound.wav" in doc and "debuff_sound.wav" in doc)
check("doc says audio degrades to silence instead of crashing", "available = False" in doc)
check("the audio section matches the mixer channel count",
      str(audio_module.MIXER_CHANNELS) in doc, f"{audio_module.MIXER_CHANNELS}")

# ---- execucao/ferramentas citados no doc existem ---------------------------
# ---- nome e empacotamento ---------------------------------------------------
check("the document is titled after the game", doc.startswith(f"# {config.TITLE}"))
check("the doc quotes the version", config.VERSION in doc)
check("the doc says the executable saves next to itself",
      "ao lado do executável" in doc)
check("the doc warns that PyInstaller does not cross-compile",
      "não cross-compila" in doc)
check("the doc documents the selftest", "--selftest" in doc)
check("the doc documents the objcopy pitfall",
      "objcopy" in doc and "libbfd" in doc)
check("the doc points at the CI workflow that builds both platforms",
      ".github/workflows/build.yml" in doc and "windows-latest" in doc
      and "ubuntu-latest" in doc)
check("the doc says the tests never touch the player's save",
      "nunca escrevam no save" in doc or "não encostam no save" in doc)
check("the gitignore exists so build output stays out of the repo",
      os.path.isfile(os.path.join(PROJECT_ROOT, ".gitignore")))
check("the packaging spec exists",
      os.path.isfile(os.path.join(PROJECT_ROOT, "quebrando_tijolos.spec")))
check("the build script exists",
      os.path.isfile(os.path.join(PROJECT_ROOT, "build.py")))

check("doc points at the test runner that exists",
      quoted("python run_tests.py")
      and os.path.isfile(os.path.join(PROJECT_ROOT, "run_tests.py")))
check("doc lists every suite that the runner actually runs",
      all(name in doc for name in ("test_physics", "test_layout", "test_powerups",
                                   "test_dynamics", "test_ui", "test_design_doc")))
check("the debug key flag exists in config",
      config.DEBUG_KEYS_ENABLED is True and quoted("DEBUG_KEYS_ENABLED"))

sys.exit(finish("documento de design"))
