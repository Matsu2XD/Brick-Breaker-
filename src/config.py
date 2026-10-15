"""Tabela central de ajustes do jogo.

Todo numero que afeta a jogabilidade mora aqui, para que balancear o jogo
nunca exija mexer na logica. Unidades: pixels e segundos.
"""

from __future__ import annotations

import os
import sys

import pygame

APP_NAME = "QuebrandoTijolos"
VERSION = "0.1 Beta"
TITLE = f"Quebrando Tijolos V {VERSION}"


def _resource_root() -> str:
    """Onde ficam os arquivos somente-leitura (assets e sons).

    Num executavel do PyInstaller eles sao extraidos para uma pasta temporaria,
    que o proprio PyInstaller anuncia em ``sys._MEIPASS``. Fora do executavel,
    sao a pasta do projeto.
    """
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return str(bundle)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _save_root() -> str:
    """Onde gravar ajustes e placar.

    Precisa ser um lugar **gravavel e permanente**. Ao lado do executavel e o que
    um jogador espera — da para levar num pendrive e o save vai junto — mas em
    ``/usr/bin`` nao da, entao ha um plano B no diretorio de dados do usuario.

    Verificar a gravabilidade na inicializacao custa uma escrita minuscula e
    evita o pior resultado possivel: o jogo rodar a sessao inteira sem gravar
    nada e o jogador perder ajustes e recordes sem nenhum aviso.
    """
    if not getattr(sys, "frozen", False):
        return os.path.join(_resource_root(), "save")

    next_to_exe = os.path.join(
        os.path.dirname(os.path.abspath(sys.executable)), "save")
    appdata = os.environ.get("APPDATA")
    user_data = (
        os.path.join(appdata, APP_NAME) if appdata
        else os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
            APP_NAME,
        )
    )

    for candidate in (next_to_exe, user_data, os.path.expanduser("~/.quebrando-tijolos")):
        try:
            os.makedirs(candidate, exist_ok=True)
            probe = os.path.join(candidate, ".escrita")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.remove(probe)
        except OSError:
            continue
        return candidate
    return user_data


PROJECT_ROOT = _resource_root()
ASSET_DIR = os.path.join(PROJECT_ROOT, "assets")
SPRITE_SHEET = os.path.join(ASSET_DIR, "Sprite Sheet", "Breakout_Tile_Free.png")
SPRITE_ATLAS = os.path.join(ASSET_DIR, "Sprite Sheet", "Breakout_Tile_Free.xml")
SOUND_DIR = os.path.join(PROJECT_ROOT, "sounds")
SAVE_DIR = _save_root()
SETTINGS_FILE = "settings.json"
SCORES_FILE = "highscores.json"

# Janela ---------------------------------------------------------------------
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720
FPS = 60
HUD_HEIGHT = 80
WALL_THICKNESS = 12

# Loop de simulacao ----------------------------------------------------------
FIXED_TIMESTEP = 1.0 / 120.0
MAX_FRAME_TIME = 0.25
MAX_SUBSTEP_RATIO = 0.5
COLLISION_SKIN = 0.1

# Area de jogo ---------------------------------------------------------------
PLAYFIELD = pygame.Rect(
    WALL_THICKNESS,
    HUD_HEIGHT + WALL_THICKNESS,
    WINDOW_WIDTH - 2 * WALL_THICKNESS,
    WINDOW_HEIGHT - HUD_HEIGHT - 2 * WALL_THICKNESS,
)

# Raquete --------------------------------------------------------------------
PADDLE_WIDTH = 116.0
PADDLE_HEIGHT = 16.0
PADDLE_BOTTOM_MARGIN = 46.0
PADDLE_SPEED = 680.0
PADDLE_PRECISION_FACTOR = 0.42
PADDLE_ENGLISH = 0.35

# Bola -----------------------------------------------------------------------
BALL_RADIUS = 9.0
BALL_SPEED = 430.0
BALL_MAX_BOUNCE_ANGLE_DEG = 62.0
BALL_MIN_VERTICAL_FRACTION = 0.22
BALL_SERVE_ANGLE_DEG = 18.0
START_LIVES = 3
LEVEL_SPEED_STEP = 0.06

# Tijolos --------------------------------------------------------------------
BRICK_ROWS = 7
BRICK_COLUMNS = 11
BRICK_HEIGHT = 26
BRICK_GAP = 6
BRICK_TOP_OFFSET = 58
BRICK_TOUGH_ROWS = 2
SCORE_PER_HIT = 10
SCORE_PER_BRICK = 100
BRICK_ROW_COLORS = (
    (255, 92, 92),
    (255, 149, 66),
    (255, 209, 92),
    (126, 217, 87),
    (90, 196, 255),
    (160, 132, 255),
    (255, 121, 198),
)

# Modificadores --------------------------------------------------------------
CAPSULE_WIDTH = 88
CAPSULE_HEIGHT = 26
CAPSULE_SPEED = 165.0
CAPSULE_DROP_CHANCE = 0.18
CAPSULE_PITY_THRESHOLD = 12
CAPSULE_BUFF_BIAS = 0.62
CAPSULE_MAX_ON_SCREEN = 4
CAPSULE_MIN_BRICKS_BEFORE_DEBUFF = 8

MAX_BALLS = 8
BALL_MULTIPLIER_FACTORS = (2, 4, 6, 8)
BALL_MULTIPLIER_WEIGHTS = (50, 28, 14, 8)
BALL_CLONE_SPREAD_DEG = 26.0

SCORE_MULTIPLIER_STEP = 2.0
SCORE_MULTIPLIER_MAX = 8.0
SCORE_MULTIPLIER_MAX_STACKS = 3

PADDLE_GROW_FACTOR = 1.25
PADDLE_GROW_MAX_STACKS = 3

GUN_SHOTS_PER_PICKUP = 8
GUN_MAX_SHOTS = 40
GUN_COOLDOWN = 0.22
GUN_LAUNCH_GRACE = 0.35
PROJECTILE_SPEED = 980.0
PROJECTILE_WIDTH = 5
PROJECTILE_HEIGHT = 15

FAST_BALLS_MULTIPLIER = 1.85
FAST_BALLS_MAX_STACKS = 2

INVADER_WIDTH = 32
INVADER_HEIGHT = 22
INVADER_SPEED_Y = 92.0
INVADER_SPEED_X = 70.0
INVADER_SPAWN_INTERVAL = 2.4
INVADER_MAX_ALIVE = 4
INVADER_SPAWN_MARGIN = 60

# Audio ----------------------------------------------------------------------
SOUND_VOLUME = 0.7
SOUND_SAMPLE_RATE = 44100
MUSIC_VOLUME = 0.45
# Qualquer arquivo em sounds/ que comece com um destes nomes e trilha, nao efeito.
MUSIC_PREFIXES = ("background_music", "music", "theme", "trilha", "bgm")

# Placar de lideres -------------------------------------------------------------
SCORES_KEPT = 8
SCORE_NAME_MAX = 12

# Sprites ----------------------------------------------------------------------
# O pack tem 10 cores de tijolo em pares: o impar e o tijolo inteiro e o par e o
# mesmo tijolo rachado. Ver sprites.py.
BRICK_ROW_SPRITES = (7, 9, 13, 3, 11, 1, 5)
SPRITE_BALL = 58
SPRITE_STAR = 59
SPRITE_HEART = 60
SPRITE_HEART_SIZE = 20
SPRITE_STAR_SIZE = 22
SPRITE_BALL_PADDING = 2

# Placar flutuante --------------------------------------------------------------
POPUP_MAX = 18
POPUP_LIFE = 0.9
POPUP_RISE = 54.0
POPUP_FONT = 20

# Ferramentas ----------------------------------------------------------------
DEBUG_KEYS_ENABLED = True

# Impacto: particulas e tremor -------------------------------------------------
PARTICLE_MAX = 420
PARTICLE_SIZE = 4
PARTICLE_GRAVITY = 460.0
PARTICLE_BRICK_COUNT = 8
PARTICLE_BRICK_SPEED = 230.0
PARTICLE_BRICK_LIFE = 0.5
PARTICLE_SPARK_COUNT = 4
PARTICLE_SPARK_SPEED = 150.0
PARTICLE_SPARK_LIFE = 0.26

SHAKE_BRICK = 1.5
SHAKE_PADDLE = 2.4
SHAKE_LIFE_LOST = 9.0
SHAKE_EVENT = 4.5
SHAKE_FINALE = 6.0
SHAKE_DECAY = 26.0
SHAKE_MAX = 14.0

# Sequencia --------------------------------------------------------------------
STREAK_REWARD_STEP = 8
STREAK_BONUS_STEP = 0.02
STREAK_BONUS_CAP = 40
STREAK_HOT = 12
STREAK_FIRE = 24

# Eventos aleatorios -----------------------------------------------------------
EVENT_FIRST_GAP = 9.0
EVENT_MIN_GAP = 15.0
EVENT_MAX_GAP = 25.0
EVENT_BANNER_TIME = 2.6
EVENT_CAPSULE_RAIN_COUNT = 5
EVENT_CAPSULE_RAIN_MAX = 9
EVENT_FRENZY_BALLS = 4
EVENT_INVASION_COUNT = 3
EVENT_INVASION_MAX = 6
EVENT_BLACKOUT_RADIUS_PADDLE = 158
EVENT_BLACKOUT_RADIUS_BALL = 116
EVENT_BLACKOUT_BAND = 22
EVENT_BLACKOUT_BANDS = 6
WILD_BALL_RAMP = 0.09
WILD_BALL_MAX = 1.9

# Reta final -------------------------------------------------------------------
FINALE_BRICKS = 5
FINALE_BALLS = 3
FINALE_SPEED_BONUS = 0.15

# Rampa dentro da fase: esvaziar a grade acelera a bola ------------------------
LEVEL_CLEAR_SPEED_RAMP = 0.12

# Cores ----------------------------------------------------------------------
COLOR_GRADIENT_TOP = (16, 18, 32)
COLOR_GRADIENT_BOTTOM = (30, 20, 48)
COLOR_HUD = (22, 26, 42)
COLOR_WALL = (52, 60, 92)
COLOR_DANGER = (120, 48, 64)
COLOR_TEXT = (232, 236, 248)
COLOR_MUTED = (132, 142, 172)
COLOR_PADDLE = (86, 214, 255)
COLOR_PADDLE_EDGE = (206, 246, 255)
COLOR_BALL = (255, 238, 176)
COLOR_BALL_CORE = (255, 255, 255)
COLOR_OVERLAY = (8, 10, 20, 205)
COLOR_MENU_VEIL = (8, 10, 22, 232)
COLOR_MENU_SELECTED = (255, 214, 102)
COLOR_CAPSULE_BUFF = (110, 231, 160)
COLOR_CAPSULE_DEBUFF = (255, 104, 128)
COLOR_CAPSULE_INNER = (16, 20, 32)
COLOR_PROJECTILE = (255, 236, 140)
COLOR_PROJECTILE_CORE = (255, 255, 235)
COLOR_INVADER = (255, 96, 140)
COLOR_INVADER_EYE = (255, 244, 220)
COLOR_GUN = (255, 206, 96)
COLOR_CHIP_BUFF = (34, 92, 66)
COLOR_CHIP_DEBUFF = (104, 34, 52)
COLOR_CHIP_TEXT = (236, 240, 250)
COLOR_PARTICLE_SPARK = (255, 246, 200)
COLOR_STREAK = (226, 234, 248)
COLOR_STREAK_HOT = (255, 206, 96)
COLOR_STREAK_FIRE = (255, 122, 96)
COLOR_EVENT_BOON = (120, 232, 168)
COLOR_EVENT_THREAT = (255, 122, 148)
COLOR_EVENT_CHAOS = (255, 206, 96)
COLOR_SAFETY_NET = (128, 236, 255)
# O que existe fora do circulo de luz no apagao: preto literal, para os tijolos
# nao vazarem nem um pouco.
COLOR_BLACKOUT = (0, 0, 0)

# Fontes ---------------------------------------------------------------------
FONT_HUD = 22
FONT_SMALL = 18
FONT_CHIP = 16
FONT_CAPSULE = 14
FONT_TITLE = 52
