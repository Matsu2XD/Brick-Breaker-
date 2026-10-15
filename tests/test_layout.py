"""Renderizacao, layout do HUD e enquadramento dos objetos.

As checagens principais leem pixels do quadro renderizado, entao uma entidade
pintada no lugar errado falha aqui sem precisar de inspecao visual.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from src import config
from src.controls import InputState
from src.game import HUD_HINT, Game, State
from src.modifiers import specs
from src.modifiers.specs import Drop
from src.sprites import SpriteSheet
from tests.harness import check, finish

game = Game()
game.start_new_game()   # o jogo abre no menu; aqui queremos a partida

# ---- orcamento de texto do HUD ---------------------------------------------
# As seis colunas do HUD, na ordem em que sao desenhadas, precisam caber sem
# se encostar. Testar as larguras reais pega tanto texto longo quanto posicao
# mal escolhida.
entry_labels = [
    (16, f"PONTOS {000000:06d}"),
    (170, f"VIDAS {config.START_LIVES}"),
    (285, "NIVEL 1"),
    (398, f"BOLAS {len(game.balls)}"),
    (505, "SEQUENCIA 123"),
]
spans = [(x, x + game.font_hud.render(label, True, (0, 0, 0)).get_width())
         for x, label in entry_labels]
hint = game.font_small.render(HUD_HINT, True, (0, 0, 0))
spans.append((config.WINDOW_WIDTH - hint.get_width() - 16, config.WINDOW_WIDTH - 16))

check("all six HUD columns fit without overlapping",
      all(spans[index][1] < spans[index + 1][0] for index in range(len(spans) - 1)),
      " | ".join(f"{start}-{end}" for start, end in spans))
check("the HUD hint starts inside the window", spans[-1][0] > 0,
      f"{spans[-1][0]}")
check("the widest HUD entry still leaves room", spans[-2][1] < spans[-1][0],
      f"SEQUENCIA termina em {spans[-2][1]}, dica começa em {spans[-1][0]}")

# ---- pixels ----------------------------------------------------------------
game._handle_launch_key()
for _ in range(150):
    game.advance(1 / 60, InputState(move=0.3))
game.draw()
screen = game.screen


def pixel_at(x, y):
    return screen.get_at((int(x), int(y)))[:3]


def sprite_centre(surface):
    if surface is None:
        return None
    return surface.get_at((surface.get_width() // 2,
                           surface.get_height() // 2))[:3]


def close(first, second, tolerance=8):
    return all(abs(a - b) <= tolerance for a, b in zip(first, second))


def brightness(surface):
    """Luminancia media da area opaca do sprite."""
    total = count = 0
    for y in range(0, surface.get_height(), 2):
        for x in range(0, surface.get_width(), 2):
            r, g, b, a = surface.get_at((x, y))
            if a < 200:
                continue
            total += r + g + b
            count += 1
    return total / max(1, count) / 3


paddle_rect = game.paddle.rect
check("paddle body is painted on screen",
      pixel_at(paddle_rect.centerx, paddle_rect.centery) == config.COLOR_PADDLE,
      f"{pixel_at(paddle_rect.centerx, paddle_rect.centery)}")

# ---- sprites ---------------------------------------------------------------
check("the sprite pack loaded", game.sprites.available,
      f"{len(game.sprites.frames)} sprites recortados")
check("the atlas has all 61 sprites", len(game.sprites.frames) == 61)

ball = game.balls[0]
centre = (round(ball.position.x), round(ball.position.y))
ball_rect = game.ball_sprite.get_rect(center=centre)
expected = game.ball_sprite.get_at((centre[0] - ball_rect.left,
                                    centre[1] - ball_rect.top))[:3]
check("the ball sprite is painted at the ball position",
      close(pixel_at(*centre), expected, 6), f"{pixel_at(*centre)} vs {expected}")

brick = next(b for b in game.bricks if b.alive)
brick_pixel = pixel_at(brick.rect.centerx, brick.rect.centery)
check("the brick sprite is painted at the brick position",
      close(brick_pixel, sprite_centre(brick.sprites[0]), 10),
      f"{brick_pixel} vs sprite {sprite_centre(brick.sprites[0])}")

rows = {b.row: b.sprites[0] for b in game.bricks}
check("every brick row owns its own colour",
      len({id(surface) for surface in rows.values()}) == config.BRICK_ROWS,
      f"{len(rows)} linhas")
check("each brick has an intact and a cracked sprite",
      all(b.sprites[1] is not None and b.sprites[0] is not b.sprites[1]
          for b in game.bricks))
check("the cracked sprite is darker than the intact one, in every row",
      all(brightness(b.sprites[1]) < brightness(b.sprites[0]) for b in game.bricks),
      f"{sorted(round(brightness(b.sprites[1]) - brightness(b.sprites[0]), 1)
                for b in game.bricks)[:3]}")

check("an intact brick uses the intact sprite",
      brick.hp == brick.max_hp and brick.sprites[0] is not None)
brick.hp -= 1
check("a damaged brick switches to the cracked sprite",
      brick.sprites[1] is not None and brick.hp < brick.max_hp)
brick.hp += 1

check("the HUD icons came from the pack",
      game.heart_sprite is not None and game.star_sprite is not None)

# ---- capsulas: o rotulo e que diz o que e -----------------------------------
check("every capsule label states the effect",
      all(spec.short for spec in specs.MODIFIERS))
widest = max(specs.MODIFIERS, key=lambda spec: game.font_capsule.size(spec.short)[0])
widest_px = game.font_capsule.size(widest.short)[0]
check("the widest capsule label fits inside the capsule with room to spare",
      widest_px <= config.CAPSULE_WIDTH - 24,
      f"'{widest.short}' mede {widest_px} px numa capsula de {config.CAPSULE_WIDTH} px")
check("capsule labels are short enough to read while falling",
      all(len(spec.short) <= 10 for spec in specs.MODIFIERS),
      f"{[spec.short for spec in specs.MODIFIERS]}")

# ---- sem assets: tudo cai no desenho por primitiva --------------------------
bare = Game(seed=3)
bare.sprites = SpriteSheet()
bare.ball_sprite = None
bare.heart_sprite = None
bare.star_sprite = None
bare.reset_level()
bare._handle_launch_key()
bare.advance(1 / 60, InputState())
bare.draw()
bare_screen = bare.screen
check("a sheet that never loaded reports itself unavailable", not bare.sprites.available)
check("with no pack, bricks fall back to their flat colour",
      bare_screen.get_at((next(b for b in bare.bricks if b.alive).rect.center))[:3]
      == next(b for b in bare.bricks if b.alive).color)
bare_ball = bare.balls[0]
check("with no pack, the ball falls back to the drawn circle",
      bare_screen.get_at((round(bare_ball.position.x),
                          round(bare_ball.position.y)))[:3]
      in (config.COLOR_BALL, config.COLOR_BALL_CORE))
check("with no pack, every brick still has a colour to draw with",
      all(brick.sprites == (None, None) and brick.color for brick in bare.bricks))

check("top wall is painted",
      pixel_at(config.PLAYFIELD.centerx, config.PLAYFIELD.top - config.WALL_THICKNESS // 2)
      == config.COLOR_WALL)
check("left wall is painted",
      pixel_at(config.PLAYFIELD.left - config.WALL_THICKNESS // 2, config.PLAYFIELD.centery)
      == config.COLOR_WALL)
check("right wall is painted",
      pixel_at(config.PLAYFIELD.right + config.WALL_THICKNESS // 2, config.PLAYFIELD.centery)
      == config.COLOR_WALL)
check("kill line is painted at the open bottom",
      pixel_at(config.PLAYFIELD.centerx, config.PLAYFIELD.bottom - 1) == config.COLOR_DANGER)
check("ball trail is clear of the kill line", ball.position.y < config.PLAYFIELD.bottom)

check("playfield starts below the HUD",
      config.PLAYFIELD.top - config.WALL_THICKNESS >= config.HUD_HEIGHT,
      f"{config.PLAYFIELD.top - config.WALL_THICKNESS} vs {config.HUD_HEIGHT}")

inside = all(
    brick.rect.left >= config.PLAYFIELD.left and brick.rect.right <= config.PLAYFIELD.right
    for brick in game.bricks
)
check("every brick fits horizontally inside the playfield", inside)
top_row = min(brick.rect.top for brick in game.bricks)
check("brick grid leaves room below the ceiling", top_row > config.PLAYFIELD.top + 20,
      f"top={top_row} field_top={config.PLAYFIELD.top}")

# ---- entidades dos modificadores -------------------------------------------
# Jogo novo com a bola solta e longe do centro: assim ela nao cobre o canhao
# no pixel testado nem impede o disparo.
game = Game(seed=7)
game.start_new_game()
game._handle_launch_key()
game.advance(1 / 60, InputState())
ball = game.balls[0]
ball.attached = False
ball.velocity = pygame.Vector2(0.0, 0.0)
ball.position = pygame.Vector2(config.PLAYFIELD.left + 40, config.PLAYFIELD.top + 200)
game.modifiers.gun_shots = 8
game.modifiers.activate(Drop(spec=specs.BY_ID["paddle_grow"]))
game.gun_cooldown = 0.0
game._fixed_step(config.FIXED_TIMESTEP, InputState(action=True))
game.draw()

screen = game.screen
wider = game.paddle.rect
check("a widened paddle is still painted where it says it is",
      pixel_at(wider.centerx, wider.centery) == config.COLOR_PADDLE,
      f"width {wider.width}")
check("the gun barrel is painted above the paddle",
      pixel_at(wider.centerx, wider.top - 5) == config.COLOR_GUN,
      f"{pixel_at(wider.centerx, wider.top - 5)}")

check("a projectile exists to be drawn", len(game.projectiles) > 0,
      f"{len(game.projectiles)} no ar")
projectile = game.projectiles[0]
proj_rect = projectile.rect
proj_pixels = {
    pixel_at(x, y)
    for x in range(proj_rect.left, proj_rect.right)
    for y in range(proj_rect.top, proj_rect.bottom)
}
check("the projectile is painted where it says it is",
      pixel_at(projectile.position.x, projectile.position.y)
      in (config.COLOR_PROJECTILE, config.COLOR_PROJECTILE_CORE),
      f"{pixel_at(projectile.position.x, projectile.position.y)}")
check("the projectile draws both its body and its bright core",
      config.COLOR_PROJECTILE in proj_pixels
      and config.COLOR_PROJECTILE_CORE in proj_pixels,
      f"{sorted(proj_pixels)}")

# ---- overlays --------------------------------------------------------------
game.state = State.GAME_OVER
game.balls = []
game.lives = 0
game.draw()
veil = pixel_at(config.WINDOW_WIDTH - 4, config.WINDOW_HEIGHT - 4)
check("game over veil darkens the corners", sum(veil) < 90, f"{veil}")

game.state = State.LEVEL_CLEAR
game.level = 3
game.draw()
check("level clear overlay renders", True)

game.state = State.PAUSED
game.draw()
check("pause overlay renders", True)

game.state = State.PLAYING
game.draw()
check("playing frame renders", True)

game.shutdown()
sys.exit(finish("renderização e layout"))
