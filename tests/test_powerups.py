"""Power-ups, debuffs, sorteio de capsulas e sistema de audio."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from src import config
from src.audio import SoundBank
from src.controls import InputState
from src.entities.ball import Ball
from src.entities.invader import Invader
from src.events import EVENTS
from src.game import Game, State
from src.modifiers import specs
from src.modifiers.capsule import Capsule
from src.modifiers.specs import Drop
from tests.harness import check, finish


def fresh(seed=1234, launch=True):
    game = Game(seed=seed)
    game.start_new_game()   # o jogo abre no menu; aqui queremos a partida
    if launch:
        game._handle_launch_key()
        game.advance(1 / 60, InputState())
    return game


def play(game, seconds, action=False, auto=True, move=None):
    """Roda a simulacao como um jogador: mantem a bola viva e persegue a mais baixa."""
    for _ in range(int(seconds * 60)):
        if game.state is not State.PLAYING or not game.balls:
            return
        if auto:
            if move is None:
                if any(ball.attached for ball in game.balls):
                    game._handle_launch_key()
                lowest = max(game.balls, key=lambda b: b.position.y)
                delta = lowest.position.x - game.paddle.center_x
                direction = 0.0 if abs(delta) <= 8 else (1.0 if delta > 0 else -1.0)
            else:
                direction = move
        else:
            direction = 0.0
        game.advance(1 / 60, InputState(move=direction, action=action))


def sides(game):
    return {round(ball.velocity.angle_to(game.balls[0].velocity), 1)
            for ball in game.balls if not ball.attached}


# ============================================================== vetores ======
check("Vector2.rotate returns a vector",
      isinstance(pygame.Vector2(0, -10).rotate(90), pygame.Vector2))

# ================================================================ audio ======
game = fresh()
check("sound bank is available under the dummy driver", game.audio.available)
check("all four wav files were loaded", len(game.audio.library) == 4,
      f"{sorted(game.audio.library)}")
for event in ("wall", "paddle", "brick", "shoot", "power_up", "debuff",
              "lose_ball", "level_complete", "game_over", "invader"):
    check(f"event '{event}' is bound to a sound", event in game.audio.sounds)
check("no event is left without a sound", not game.audio.missing, f"{game.audio.missing}")
check("every event owns a dedicated channel",
      all(event in game.audio.channels for event in game.audio.sounds))

game.audio.play("brick")
check("playing an event does not raise", True)
game.audio.play("nao_existe")
check("unknown events are ignored", True)

check("M mutes the audio", game.audio.toggle_mute() is True and game.audio.muted)
check("M unmutes the audio", game.audio.toggle_mute() is False and not game.audio.muted)

silent = SoundBank()
silent.available = False
silent.play("brick")
check("a bank without a mixer degrades to silence", True)

# ================================================ multiplicador de bolas ====
game = fresh()
start_count = len(game.balls)
game._collect(Drop(spec=specs.BY_ID["ball_multiplier"], magnitude=2))
check("2x doubles the balls", len(game.balls) == start_count * 2,
      f"{start_count} -> {len(game.balls)}")
check("every cloned ball keeps the effective speed",
      all(abs(ball.speed - game.ball_speed) < 1e-6
          for ball in game.balls if not ball.attached),
      f"{[round(b.speed, 1) for b in game.balls]}")
check("clones do not all fly the same direction", len(sides(game)) > 1, f"{sides(game)}")

game._collect(Drop(spec=specs.BY_ID["ball_multiplier"], magnitude=8))
check("8x is capped at MAX_BALLS", len(game.balls) == config.MAX_BALLS,
      f"{len(game.balls)} (cap {config.MAX_BALLS})")
game._collect(Drop(spec=specs.BY_ID["ball_multiplier"], magnitude=8))
check("the cap cannot be exceeded", len(game.balls) == config.MAX_BALLS)

for factor in (4, 6, 8):
    clone_game = fresh()
    while len(clone_game.balls) * factor <= config.MAX_BALLS:
        clone_game.balls.append(Ball(position=pygame.Vector2(0, 0)))
    clone_game._collect(Drop(spec=specs.BY_ID["ball_multiplier"], magnitude=factor))
    check(f"{factor}x multiplies the current balls",
          len(clone_game.balls) == config.MAX_BALLS, f"{len(clone_game.balls)}")

# ============================================== multiplicador de pontos ====
game = fresh()
check("score multiplier starts at 1x", game.modifiers.score_multiplier == 1.0)
for expected in (2.0, 4.0, 8.0, 8.0):
    game._collect(Drop(spec=specs.BY_ID["score_multiplier"]))
    check(f"score multiplier reaches {expected:g}x",
          game.modifiers.score_multiplier == expected, f"{game.modifiers.score_multiplier}")

weak_brick = next(b for b in game.bricks if b.alive and b.max_hp == 1)
check("the streak starts at zero", game.streak == 0)
expected = int(weak_brick.score_value * game.modifiers.score_multiplier
               * game.streak_bonus)
before = game.score
game._damage_brick(weak_brick)
gained = game.score - before
check("a destroyed brick pays the multiplier",
      gained == expected == weak_brick.score_value * 8, f"{gained} vs {expected}")
check("destroying really removed the brick", not weak_brick.alive)
check("destroying a brick raises the streak", game.streak == 1)

tough_brick = next(b for b in game.bricks if b.alive and b.max_hp == 2)
expected = int(config.SCORE_PER_HIT * game.modifiers.score_multiplier
               * game.streak_bonus)
check("the streak now pays a small bonus", game.streak_bonus > 1.0,
      f"x{game.streak_bonus:.2f}")
before = game.score
game._damage_brick(tough_brick)
check("a surviving brick pays the hit value times both multipliers",
      game.score - before == expected, f"{game.score - before} vs {expected}")

check("no multiplier means raw points", Game(seed=1).modifiers.score_multiplier == 1.0)

# ================================================= aumento da bandeja ======
game = fresh()
base_width = game.paddle.width
game._collect(Drop(spec=specs.BY_ID["paddle_grow"]))
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("WIDE widens the paddle",
      abs(game.paddle.width - base_width * config.PADDLE_GROW_FACTOR) < 0.01,
      f"{base_width} -> {game.paddle.width}")

centre_before = game.paddle.center_x
game._collect(Drop(spec=specs.BY_ID["paddle_grow"]))
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("growing keeps the paddle centred",
      abs(game.paddle.center_x - centre_before) < 1.0,
      f"{centre_before} -> {game.paddle.center_x}")
check("WIDE stacks", abs(game.paddle.width - base_width * 1.5) < 0.01, f"{game.paddle.width}")

for _ in range(3):
    game._collect(Drop(spec=specs.BY_ID["paddle_grow"]))
    game._fixed_step(config.FIXED_TIMESTEP, InputState())
ceiling = base_width * (1 + 0.25 * config.PADDLE_GROW_MAX_STACKS)
check("WIDE stops stacking at the cap", abs(game.paddle.width - ceiling) < 0.01,
      f"{game.paddle.width} vs {ceiling}")

game.paddle.position.x = -500
game.paddle._clamp_to_playfield()
check("a wide paddle stays inside the left wall",
      game.paddle.rect.left >= config.PLAYFIELD.left)
game.paddle.position.x = 5000
game.paddle._clamp_to_playfield()
check("a wide paddle stays inside the right wall",
      game.paddle.rect.right <= config.PLAYFIELD.right)

game.modifiers.effects.clear()
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("WIDE reverts when it expires", abs(game.paddle.width - base_width) < 0.01,
      f"{game.paddle.width}")

# =============================================================== canhao =====
game = fresh()
game._collect(Drop(spec=specs.BY_ID["gun"]))
check("GUN grants a limited magazine",
      game.modifiers.gun_shots == config.GUN_SHOTS_PER_PICKUP,
      f"{game.modifiers.gun_shots} shots")
check("GUN shows on the paddle", game.modifiers.gun_active)

play(game, 0.1, action=True)
check("the launch press does not waste ammo",
      game.modifiers.gun_shots == config.GUN_SHOTS_PER_PICKUP, f"{game.modifiers.gun_shots}")

game.gun_cooldown = 0.0
play(game, 1.0, action=True)
fired = config.GUN_SHOTS_PER_PICKUP - game.modifiers.gun_shots
ideal = 1.0 / config.GUN_COOLDOWN
check("holding the action key shoots", fired >= 3, f"{fired} shots")
check("the fire rate respects the cooldown", abs(fired - ideal) <= 1.5,
      f"{fired} shots in 1,0 s (cooldown {config.GUN_COOLDOWN}s)")

game = fresh()
game._collect(Drop(spec=specs.BY_ID["gun"]))
living_before = sum(1 for b in game.bricks if b.alive)
play(game, 2.0, action=True)
living_after = sum(1 for b in game.bricks if b.alive)
check("projectiles destroy bricks", living_after < living_before,
      f"{living_before} -> {living_after}")

game.modifiers.gun_shots = 1
game.gun_cooldown = 0.0
game._fixed_step(config.FIXED_TIMESTEP, InputState(action=True))
check("the gun stops at zero ammo", game.modifiers.gun_shots == 0)
game.gun_cooldown = 0.0
projectiles_before = len(game.projectiles)
game._fixed_step(config.FIXED_TIMESTEP, InputState(action=True))
check("an empty gun fires nothing", len(game.projectiles) <= projectiles_before)

# ================================================ inversao dos comandos ====
game = fresh()
game._collect(Drop(spec=specs.BY_ID["inverted_controls"]))
check("SWAP registers as a timed effect", game.modifiers.controls_inverted)

game.advance(1 / 60, InputState(move=1.0))
left_of_start = game.paddle.position.x
check("SWAP makes right move the paddle left", left_of_start < 422.0,
      f"422.0 -> {left_of_start:.2f}")

game.advance(1 / 60, InputState(move=-1.0))
check("SWAP makes left move the paddle right", game.paddle.position.x > left_of_start,
      f"{left_of_start:.2f} -> {game.paddle.position.x:.2f}")

game.modifiers.effects.clear()
before = game.paddle.position.x
game.advance(1 / 60, InputState(move=1.0))
check("controls go back to normal when SWAP expires", game.paddle.position.x > before)

# ================================================= bolas super rapidas =====
game = fresh()
base_speed = game.ball_speed
game._collect(Drop(spec=specs.BY_ID["fast_balls"]))
game._fixed_step(config.FIXED_TIMESTEP, InputState())
expected = base_speed * config.FAST_BALLS_MULTIPLIER
check("FAST raises the effective speed", abs(game.ball_speed - expected) < 1e-6,
      f"{game.ball_speed:.1f}")
check("FAST is applied to balls already in play",
      all(abs(ball.speed - expected) < 1e-6 for ball in game.balls),
      f"{[round(b.speed, 1) for b in game.balls]}")

game.modifiers.effects.clear()
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("balls slow back down when FAST expires",
      all(abs(ball.speed - base_speed) < 1e-6 for ball in game.balls),
      f"{[round(b.speed, 1) for b in game.balls]}")

for _ in range(4):
    game._collect(Drop(spec=specs.BY_ID["fast_balls"]))
capped = base_speed * config.FAST_BALLS_MULTIPLIER**config.FAST_BALLS_MAX_STACKS
check("FAST stacking is capped", abs(game.ball_speed - capped) < 1e-6,
      f"{game.ball_speed:.1f} vs {capped:.1f}")
check("FAST is a debuff", specs.BY_ID["fast_balls"].polarity is specs.Polarity.DEBUFF)

# =========================================================== invasores ======
game = fresh(launch=False)
check("no invaders before the debuff", not game.invaders)
game._collect(Drop(spec=specs.BY_ID["invaders"]))
check("ALIEN starts the invasion window", game.modifiers.invaders_active)

play(game, config.INVADER_SPAWN_INTERVAL + 0.3, auto=False)
check("invaders spawn over time", len(game.invaders) >= 1,
      f"{len(game.invaders)} após {config.INVADER_SPAWN_INTERVAL + 0.3:.1f}s")
check("invaders descend", all(invader.velocity.y > 0 for invader in game.invaders))
check("invaders stay between the walls",
      all(invader.rect.left >= config.PLAYFIELD.left
          and invader.rect.right <= config.PLAYFIELD.right for invader in game.invaders))

play(game, 3.0)
check("the invader count is capped", len(game.invaders) <= config.INVADER_MAX_ALIVE,
      f"{len(game.invaders)}")

lives_before = game.lives
game.invaders = [Invader(
    position=pygame.Vector2(game.paddle.center_x, game.paddle.rect.centery),
    velocity=pygame.Vector2(0.0, config.INVADER_SPEED_Y),
)]
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("an invader hitting the paddle costs a life", game.lives == lives_before - 1,
      f"{lives_before} -> {game.lives}")
check("the invader is removed after the hit", len(game.invaders) == 0)

game = fresh()
game._collect(Drop(spec=specs.BY_ID["gun"]))
# A bola fica congelada e longe da coluna do invasor, para o teste medir so o canhao.
game.balls[0].velocity = pygame.Vector2(0.0, 0.0)
game.balls[0].position = pygame.Vector2(config.PLAYFIELD.left + 30,
                                        config.PLAYFIELD.bottom - 30)
game.invaders = [Invader(
    position=pygame.Vector2(game.paddle.center_x, config.PLAYFIELD.bottom - 120),
    velocity=pygame.Vector2(0.0, 0.0),
)]
play(game, 0.8, action=True, auto=False)
check("projectiles destroy invaders", len(game.invaders) == 0, f"{len(game.invaders)} left")

game = fresh()
game.invaders = [Invader(
    position=pygame.Vector2(game.balls[0].position.x, game.balls[0].position.y + 40),
    velocity=pygame.Vector2(0.0, 0.0),
)]
play(game, 1.0)
check("the ball destroys invaders", len(game.invaders) == 0, f"{len(game.invaders)}")

game = fresh(launch=False)
game.invaders = [Invader(
    position=pygame.Vector2(config.PLAYFIELD.centerx, config.PLAYFIELD.bottom + 60),
    velocity=pygame.Vector2(0.0, config.INVADER_SPEED_Y),
)]
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("an invader below the field is cleaned up", len(game.invaders) == 0)

# ============================================================== capsules ====
game = fresh()
expected_events = {"ball_multiplier", "score_multiplier", "paddle_grow", "gun",
                   "inverted_controls", "fast_balls", "invaders"}
check("the catalogue holds the 4 buffs and 3 debuffs the brief asked for",
      {spec.id for spec in specs.MODIFIERS} == expected_events,
      f"{sorted(spec.id for spec in specs.MODIFIERS)}")
check("every capsule renders a label",
      all(Drop(spec=s, magnitude=8).label for s in specs.MODIFIERS))

game.capsules = [Capsule.falling_from(
    Drop(spec=specs.BY_ID["paddle_grow"]),
    (game.paddle.rect.centerx, game.paddle.rect.top - 30),
)]
play(game, 1.0)
check("a capsule is caught by the paddle",
      not game.capsules and "paddle_grow" in game.modifiers.effects)

game.capsules = [Capsule.falling_from(
    Drop(spec=specs.BY_ID["fast_balls"]),
    (config.PLAYFIELD.left + 5, config.PLAYFIELD.top + 5),
)]
game.paddle.position.x = config.PLAYFIELD.right - game.paddle.width
play(game, 6.0, move=1.0, auto=False)
check("a missed capsule falls out of play", not game.capsules)

# ================================================================ sorteio ===
roller = Game(seed=7)
rolls = [roller.modifiers.roll_drop(at_ball_cap=False) for _ in range(4000)]
drops = [drop for drop in rolls if drop is not None]
rate = len(drops) / len(rolls)
check("drops happen at roughly the configured rate", 0.15 < rate < 0.30,
      f"{rate:.0%} (configurado {config.CAPSULE_DROP_CHANCE:.0%})")
check("both polarities show up in the long run",
      any(d.is_buff for d in drops) and any(not d.is_buff for d in drops))

pity = Game(seed=11)
pity.modifiers.bricks_destroyed = 200
longest_dry = current = 0
for _ in range(4000):
    if pity.modifiers.roll_drop(at_ball_cap=False) is None:
        current += 1
        longest_dry = max(longest_dry, current)
    else:
        current = 0
check("a dry streak never exceeds the pity threshold",
      longest_dry <= config.CAPSULE_PITY_THRESHOLD,
      f"maior seca {longest_dry} (limite {config.CAPSULE_PITY_THRESHOLD})")

pity.modifiers.bricks_since_drop = config.CAPSULE_PITY_THRESHOLD
check("the pity rule forces the next drop",
      pity.modifiers.roll_drop(at_ball_cap=False) is not None)

early = Game(seed=3)
early.modifiers.bricks_destroyed = 1
picks = [early.modifiers._pick(at_ball_cap=False) for _ in range(400)]
check("no debuff drops in the opening bricks", all(d.is_buff for d in picks),
      f"{[d.spec.id for d in picks if not d.is_buff][:3]}")

late = Game(seed=3)
late.modifiers.bricks_destroyed = 200
picks = [late.modifiers._pick(at_ball_cap=False) for _ in range(600)]
buff_ratio = sum(1 for d in picks if d.is_buff) / len(picks)
check("buffs stay more likely than debuffs", 0.5 < buff_ratio < 0.8,
      f"{buff_ratio:.0%} buffs")

at_cap = Game(seed=5)
at_cap.modifiers.bricks_destroyed = 200
check("no ball multiplier drops at the ball cap",
      all(d.spec.id != "ball_multiplier"
          for d in (at_cap.modifiers._pick(at_ball_cap=True) for _ in range(300))))

maxed = Game(seed=5)
maxed.modifiers.score_stacks = config.SCORE_MULTIPLIER_MAX_STACKS
maxed.modifiers.bricks_destroyed = 300
check("no score multiplier drops past its cap",
      all(d.spec.id != "score_multiplier"
          for d in (maxed.modifiers._pick(at_ball_cap=False) for _ in range(300))))

active_only = Game(seed=5)
active_only.modifiers.bricks_destroyed = 300
active_only.modifiers.activate(Drop(spec=specs.BY_ID["fast_balls"]))
check("an effect that is already running is not dropped again",
      all(d.spec.id != "fast_balls"
          for d in (active_only.modifiers._pick(at_ball_cap=False) for _ in range(300))))

# ============================================== morte e persistencia =======
game = fresh()
game._collect(Drop(spec=specs.BY_ID["fast_balls"]))
game._collect(Drop(spec=specs.BY_ID["paddle_grow"]))
game._collect(Drop(spec=specs.BY_ID["gun"]))
game.modifiers.score_stacks = 2
game._lose_life()
check("losing a life clears the buffs", "paddle_grow" not in game.modifiers.effects)
check("losing a life clears the ammo", game.modifiers.gun_shots == 0)
check("losing a life does NOT clear the debuffs",
      "fast_balls" in game.modifiers.effects,
      "senão bastaria morrer de propósito para se livrar da punição")
check("losing a life keeps the score accumulation",
      game.modifiers.score_multiplier == 4.0)

game.reset_level()
check("a new level clears everything timed", not game.modifiers.effects)
check("a new level keeps the score accumulation",
      game.modifiers.score_multiplier == 4.0)

# ============================================================== integral ====
game = fresh(seed=2024)
play(game, 60.0)
check("score accumulates with modifiers active", game.score > 0, f"score={game.score}")
check("lives stay in range", 0 <= game.lives <= config.START_LIVES, f"lives={game.lives}")
check("balls never exceed the cap", len(game.balls) <= config.MAX_BALLS, f"{len(game.balls)}")
check("timed effects always have time left",
      all(effect.remaining > 0 for effect in game.modifiers.timed_effects()))
check("ball speed is always exactly the effective speed",
      all(abs(b.speed - game.ball_speed) < 1e-6 or b.attached for b in game.balls),
      f"{[round(b.speed, 1) for b in game.balls]}")
check("effect keys always match their specs",
      all(key == effect.spec.id for key, effect in game.modifiers.effects.items()))

# =========================================================== ferramentas ====
game = fresh()
game._debug_spawn(specs.BY_ID["paddle_grow"])
check("the debug key drops a capsule above the paddle", len(game.capsules) == 1)
game._debug_clear()
check("0 clears effects and capsules", not game.capsules and not game.modifiers.effects)

game._debug_spawn(specs.BY_ID["ball_multiplier"])
first = game.capsules[0].drop.magnitude
game._debug_spawn(specs.BY_ID["ball_multiplier"])
second = game.capsules[1].drop.magnitude
check("the debug ball multiplier cycles through the factors",
      first != second and {first, second} <= set(config.BALL_MULTIPLIER_FACTORS),
      f"{first} then {second}")

# ================================================================== HUD =====
game = fresh()
game._collect(Drop(spec=specs.BY_ID["paddle_grow"]))
game._collect(Drop(spec=specs.BY_ID["score_multiplier"]))
game._collect(Drop(spec=specs.BY_ID["gun"]))
game._collect(Drop(spec=specs.BY_ID["invaders"]))
game.draw()

check("every modifier has a capsule label and a chip name",
      all(spec.short and spec.hud for spec in specs.MODIFIERS))
check("capsule labels say what the modifier does, not an abbreviation",
      all(len(spec.short) >= 5 for spec in specs.MODIFIERS),
      f"{[spec.short for spec in specs.MODIFIERS]}")


def chip_width(label):
    return game.font_chip.size(label)[0] + 18 + 8


# A pergunta que importa: a carga maxima cabe ao lado do resumo?
modifier_chips = [f"{spec.hud}  {int(spec.duration)}s"
                  for spec in specs.MODIFIERS if spec.duration > 0]
event_chips = sorted((f"{spec.chip}  12s" for spec in EVENTS),
                     key=chip_width, reverse=True)
summary = "PONTOS x8     TIROS 40     MUDO"
reserved = game.font_chip.size(summary)[0] + 16
available = config.WINDOW_WIDTH - 16 - (reserved + 20)
worst = sum(chip_width(label) for label in modifier_chips)
worst += chip_width(event_chips[0]) + chip_width(event_chips[1])
check("the worst-case chip load fits beside the summary", worst <= available,
      f"{worst} px de chips para {available} px disponiveis")
check("every event has a chip name no longer than its full name",
      all(spec.chip and len(spec.chip) <= len(spec.name) for spec in EVENTS))
check("all four timed modifiers can be shown at once",
      len(modifier_chips) == 4, f"{modifier_chips}")

light = sum(chip_width(f"{spec.hud}  {int(spec.duration)}s") for spec in specs.BUFFS
            if spec.duration > 0)
check("a single buff chip is nowhere near the limit", light < available / 3,
      f"{light} vs {available}")

check("the HUD is tall enough for two rows", config.HUD_HEIGHT >= 76, f"{config.HUD_HEIGHT}")
check("the playfield still starts below the HUD",
      config.PLAYFIELD.top - config.WALL_THICKNESS >= config.HUD_HEIGHT)

# ============================================================ fim de jogo ===
game = fresh()
game.lives = 1
game.balls = [Ball(position=pygame.Vector2(config.PLAYFIELD.centerx,
                                           config.PLAYFIELD.bottom + 50))]
game.balls[0].attached = False
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("game over still works with modifiers wired in",
      game.state is State.GAME_OVER, f"{game.state}")
check("game over clears the power-ups",
      not game.modifiers.effects and game.modifiers.gun_shots == 0)

game.shutdown()
sys.exit(finish("power-ups, debuffs e áudio"))
