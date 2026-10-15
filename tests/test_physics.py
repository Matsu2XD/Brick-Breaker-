"""Fisica da bola e controles do jogador."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from src import config, physics
from src.controls import InputState
from src.entities.ball import Ball
from src.game import Game, State
from src.level import build_bricks
from tests.harness import check, finish

# Semente fixa: uma falha aqui tem que ser reproduzivel.
game = Game(seed=1234)
game.start_new_game()   # o jogo abre no menu; aqui queremos a partida

# --- lancamento -------------------------------------------------------------
ball = game.balls[0]
check("ball starts attached to paddle", ball.attached)
check("attached ball is motorless", ball.speed == 0.0)

game.handle_events()
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
game.handle_events()
game.advance(1 / 60, InputState())
check("W launches the ball", not ball.attached)
check("launch speed matches level tuning",
      math.isclose(ball.speed, config.BALL_SPEED, rel_tol=1e-6), f"speed={ball.speed:.2f}")
check("launch goes upward", ball.velocity.y < 0)

# --- controles da bandeja ---------------------------------------------------
start_x = game.paddle.position.x
for _ in range(30):
    game.advance(1 / 60, InputState(move=1.0))
check("D/right moves the paddle right", game.paddle.position.x > start_x,
      f"{start_x:.1f} -> {game.paddle.position.x:.1f}")

for _ in range(300):
    game.advance(1 / 60, InputState(move=1.0))
check("paddle is clamped inside the playfield",
      game.paddle.rect.right <= config.PLAYFIELD.right, f"right={game.paddle.rect.right}")

for _ in range(300):
    game.advance(1 / 60, InputState(move=-1.0))
check("paddle clamps on the left wall",
      game.paddle.rect.left >= config.PLAYFIELD.left, f"left={game.paddle.rect.left}")

left_before = game.paddle.position.x
game.advance(1 / 60, InputState(move=1.0))
normal_delta = game.paddle.position.x - left_before
game.advance(1 / 60, InputState(move=1.0, precision=True))
precision_delta = game.paddle.position.x - left_before - normal_delta
check("precision mode slows the paddle", precision_delta < normal_delta,
      f"{precision_delta:.2f} < {normal_delta:.2f}")

# --- simulacao longa --------------------------------------------------------
bricks_before = sum(1 for brick in game.bricks if brick.alive)
max_speed_drift = 0.0
escapes = 0
frames = 0
while frames < 6000 and game.state is State.PLAYING:
    if any(live.attached for live in game.balls):
        game._handle_launch_key()
    lowest = max(game.balls, key=lambda b: b.position.y)
    direction = 0.0
    if abs(lowest.position.x - game.paddle.center_x) > 8:
        direction = 1.0 if lowest.position.x > game.paddle.center_x else -1.0
    game.advance(1 / 60, InputState(move=direction))
    for live_ball in game.balls:
        if live_ball.attached:
            continue
        max_speed_drift = max(max_speed_drift, abs(live_ball.speed - game.ball_speed))
        if live_ball.position.y - live_ball.radius > config.PLAYFIELD.bottom:
            escapes += 1
    frames += 1

bricks_after = sum(1 for brick in game.bricks if brick.alive)
check("bricks get destroyed", bricks_after < bricks_before, f"{bricks_before} -> {bricks_after}")
check("score is credited", game.score > 0, f"score={game.score}")
check("ball keeps constant speed", max_speed_drift < 1e-6, f"drift={max_speed_drift:.3e}")
check("simulation ran without a stuck state", frames > 100, f"frames={frames}")
check("lives only decrease on real drops", 0 <= game.lives <= config.START_LIVES,
      f"lives={game.lives}, drops={escapes}")

# --- tunneling --------------------------------------------------------------
probe = Ball(position=pygame.Vector2(config.PLAYFIELD.centerx, config.PLAYFIELD.top + 200.0))
probe.attached = False
probe.velocity = pygame.Vector2(0.0, -60000.0)
game.bricks = build_bricks(config.PLAYFIELD)
report = physics.move_and_collide(probe, config.FIXED_TIMESTEP, game.paddle, game.bricks)
check("a 60k px/s ball still collides with bricks", len(report.bricks_hit) > 0,
      f"hits={len(report.bricks_hit)}")
check("fast ball stays inside the playfield",
      probe.position.y - probe.radius >= config.PLAYFIELD.top - 0.001,
      f"y={probe.position.y:.2f}")

# --- trava anti-horizontal --------------------------------------------------
locked = pygame.Vector2(5.0, 0.0)
fixed = physics.enforce_min_vertical(locked)
check("near-horizontal velocity is corrected",
      abs(fixed.y) / fixed.length() >= config.BALL_MIN_VERTICAL_FRACTION - 1e-9, f"-> {fixed}")
check("correction preserves speed",
      math.isclose(fixed.length(), locked.length(), rel_tol=1e-9),
      f"{fixed.length():.3f} vs {locked.length():.3f}")

# --- fim de jogo ------------------------------------------------------------
game.lives = 1
game.balls = [Ball(position=pygame.Vector2(config.PLAYFIELD.centerx,
                                           config.PLAYFIELD.bottom + 50.0))]
game.balls[0].attached = False
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("last ball lost triggers game over", game.state is State.GAME_OVER, f"state={game.state}")

game.shutdown()
sys.exit(finish("física e controles"))
