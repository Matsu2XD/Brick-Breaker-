"""Dinamica: particulas, tremor, sequencia, eventos aleatorios e reta final."""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from src import config
from src.controls import InputState
from src.entities.ball import Ball
from src.entities.particle import ParticleSystem
from src.events import BY_ID as EVENT_SPECS
from src.events import EVENTS, EventDirector, Mood, mood_color
from src.game import Game, State
from src.modifiers import specs
from src.modifiers.specs import Drop
from tests.harness import check, finish


def fresh(seed=1234, launch=True):
    game = Game(seed=seed)
    game.start_new_game()   # o jogo abre no menu; aqui queremos a partida
    if launch:
        game._handle_launch_key()
        game.advance(1 / 60, InputState())
    return game


def play(game, seconds, action=False, auto=True):
    for _ in range(int(seconds * 60)):
        if game.state is not State.PLAYING or not game.balls:
            return
        if auto and any(ball.attached for ball in game.balls):
            game._handle_launch_key()
        direction = 0.0
        if auto:
            lowest = max(game.balls, key=lambda b: b.position.y)
            delta = lowest.position.x - game.paddle.center_x
            direction = 0.0 if abs(delta) <= 8 else (1.0 if delta > 0 else -1.0)
        game.advance(1 / 60, InputState(move=direction, action=action))


# ============================================================ particulas ====
system = ParticleSystem(random.Random(0))
check("a new particle system is empty", len(system) == 0)

system.burst((100, 100), (255, 0, 0), 1, 0.0, 0.5)
check("a burst creates exactly the requested particles", len(system) == 1)

surface = pygame.Surface((200, 200))
surface.fill((0, 0, 0))
system.draw(surface)
check("a particle is painted where it was born",
      surface.get_at((100, 100))[:3] == (255, 0, 0),
      f"{surface.get_at((100, 100))[:3]}")

system.clear()
check("clear empties the system", len(system) == 0)

for _ in range(200):
    system.burst((100, 100), (255, 0, 0), 8, 200.0, 0.5)
check("the particle count is capped", len(system) == config.PARTICLE_MAX,
      f"{len(system)} (cap {config.PARTICLE_MAX})")

before_y = [particle.velocity.y for particle in system.particles]
system.update(0.05)
check("gravity pulls the particles down",
      all(particle.velocity.y > before for particle, before in
          zip(system.particles, before_y)),
      f"{before_y[0]:.1f} -> {system.particles[0].velocity.y:.1f}")
check("particles shrink as they die",
      all(0.0 <= particle.fade <= 1.0 for particle in system.particles))

system.update(1.0)
check("dead particles are removed", len(system) == 0, f"{len(system)} left")

# ================================================================ tremor ====
game = fresh()
check("no shake at rest", game.shake == 0.0 and game.shake_offset == (0, 0))

game._add_shake(config.SHAKE_LIFE_LOST)
check("shake can be raised", game.shake == config.SHAKE_LIFE_LOST)
game._add_shake(config.SHAKE_MAX * 5)
check("shake is capped", game.shake == config.SHAKE_MAX, f"{game.shake}")

offsets = set()
for _ in range(40):
    game.advance(1 / 60, InputState())
    offsets.add(game.shake_offset)
check("shake actually displaces the world", len(offsets) > 3, f"{len(offsets)} posicoes")

play(game, 2.0)
check("shake decays back to nothing", game.shake == 0.0, f"{game.shake}")

game = fresh()
game._damage_brick(next(b for b in game.bricks if b.alive and b.max_hp == 1))
check("breaking a brick kicks the screen", game.shake > 0.0, f"{game.shake}")

game = fresh()
game.lives = 2
game._lose_life()
check("losing a life kicks the screen harder",
      game.shake >= config.SHAKE_LIFE_LOST, f"{game.shake}")

# ============================================================= sequencia ====
game = fresh()
weak = [brick for brick in game.bricks if brick.alive and brick.max_hp == 1]
check("the streak starts at zero", game.streak == 0)
check("a zero streak pays no bonus", game.streak_bonus == 1.0)

game._damage_brick(weak[0])
check("destroying a brick raises the streak", game.streak == 1)
check("the bonus grows with the streak", game.streak_bonus > 1.0)

for brick in weak[1:6]:
    game._damage_brick(brick)
check("the streak keeps climbing", game.streak == 6, f"{game.streak}")

game.streak = config.STREAK_BONUS_CAP + 50
check("the streak bonus is capped",
      abs(game.streak_bonus - (1 + config.STREAK_BONUS_CAP * config.STREAK_BONUS_STEP))
      < 1e-9, f"x{game.streak_bonus:.2f}")

check("the streak colour escalates",
      Game(seed=1).streak_color == config.COLOR_STREAK)
hot = fresh()
hot.streak = config.STREAK_HOT
check("a hot streak changes colour", hot.streak_color == config.COLOR_STREAK_HOT)
fire = fresh()
fire.streak = config.STREAK_FIRE
check("a blazing streak changes colour again", fire.streak_color == config.COLOR_STREAK_FIRE)

# a recompensa de sequencia e garantida, nao sorteada
game = fresh()
game.bricks_destroyed_level = 0
granted = []
original = game.modifiers.force_drop
game.modifiers.force_drop = lambda at_ball_cap=False: (
    granted.append(1), original(at_ball_cap=at_ball_cap))[1]
game.streak = config.STREAK_REWARD_STEP - 1
game._damage_brick(next(b for b in game.bricks if b.alive and b.max_hp == 1))
check("every N bricks the player earns a guaranteed capsule",
      len(granted) == 1, f"{len(granted)} recompensas")
game.modifiers.force_drop = original

game = fresh()
game.streak = 9
game.lives = 3
game._lose_life()
check("losing a ball resets the streak", game.streak == 0)

# ============================================================== eventos =====
check("the catalogue has both helpful and harmful events",
      any(spec.mood is Mood.BOON for spec in EVENTS)
      and any(spec.mood is Mood.THREAT for spec in EVENTS)
      and len(EVENTS) == 7, f"{len(EVENTS)} eventos")
check("every event has a colour", all(mood_color(spec.mood) for spec in EVENTS))

planner = Game(seed=5)
check("nothing is running at the start", not planner.events.running)
check("the first event is scheduled",
      0.0 < planner.events.next_in <= config.EVENT_FIRST_GAP, f"{planner.events.next_in}")

game = fresh()
play(game, config.EVENT_FIRST_GAP + 0.2)
check("an event fires on schedule", game._banner is not None,
      f"{game._banner.text if game._banner else None}")
check("the event is announced by name",
      game._banner is None or game._banner.text in [spec.name for spec in EVENTS])
check("the director rescheduled the next event",
      0.0 < game.events.next_in <= config.EVENT_MAX_GAP, f"{game.events.next_in}")

# Um director novo: eventos com duracao que ja estao rodando nao voltam a ser
# sorteados, entao a lista precisa comecar vazia para cobrir o catalogo inteiro.
picker = Game(seed=5)
consecutive = [picker.events.force_next().id for _ in range(200)]
check("the same event never fires twice in a row",
      all(a != b for a, b in zip(consecutive, consecutive[1:])),
      f"{[pair for pair in zip(consecutive, consecutive[1:]) if pair[0] == pair[1]][:3]}")

covered = set(consecutive)
check("every event in the catalogue can come up", covered == set(EVENT_SPECS),
      f"faltando: {sorted(set(EVENT_SPECS) - covered)}")

# --- cada evento faz o que promete
game = fresh()
game.capsules.clear()
game._fire_event(EVENT_SPECS["capsule_rain"])
check("CHUVA DE CAPSULAS drops a handful at once",
      len(game.capsules) == config.EVENT_CAPSULE_RAIN_COUNT,
      f"{len(game.capsules)} capsulas")
check("the rain announces itself",
      game._banner is not None and game._banner.text == EVENT_SPECS["capsule_rain"].name)

game = fresh()
game._fire_event(EVENT_SPECS["ball_frenzy"])
check("FRENESI DE BOLAS fills the field",
      len(game.balls) == config.EVENT_FRENZY_BALLS, f"{len(game.balls)} bolas")

game = fresh()
check("no invaders before the invasion", not game.invaders)
game._fire_event(EVENT_SPECS["invasion"])
check("INVASAO brings a wave",
      len(game.invaders) == config.EVENT_INVASION_COUNT, f"{len(game.invaders)}")
check("the invasion is a threat", EVENT_SPECS["invasion"].mood is Mood.THREAT)

game = fresh()
game.modifiers.gun_shots = 0
game._fire_event(EVENT_SPECS["free_gun"])
check("TIRO LIVRE is running", game.events.is_running("free_gun"))
check("TIRO LIVRE arms the paddle with no ammo", game.gun_ready)
game.gun_cooldown = 0.0
game.balls[0].attached = False
game._fixed_step(config.FIXED_TIMESTEP, InputState(action=True))
check("TIRO LIVRE actually fires", len(game.projectiles) > 0, f"{len(game.projectiles)}")
check("TIRO LIVRE does not spend ammo", game.modifiers.gun_shots == 0)

game = fresh()
game._fire_event(EVENT_SPECS["wild_ball"])
check("BOLA LOUCA starts at normal speed",
      abs(game.events.ball_speed_multiplier - 1.0) < 0.05)
play(game, 4.0)
check("BOLA LOUCA accelerates over time",
      game.events.ball_speed_multiplier > 1.2,
      f"x{game.events.ball_speed_multiplier:.2f}")
check("the ball actually speeds up",
      all(ball.speed > config.BALL_SPEED for ball in game.balls if not ball.attached),
      f"{[round(b.speed) for b in game.balls]}")

play(game, 6.0)
check("BOLA LOUCA is capped", game.events.ball_speed_multiplier <= config.WILD_BALL_MAX)
check("BOLA LOUCA ends", not game.events.is_running("wild_ball"))

game = fresh()
game._fire_event(EVENT_SPECS["blackout"])
check("APAGAO is running", game.events.is_running("blackout"))
check("APAGAO is a threat", EVENT_SPECS["blackout"].mood is Mood.THREAT)

game = fresh()
game._fire_event(EVENT_SPECS["safety_net"])
check("REDE DE SEGURANCA is running", game.events.is_running("safety_net"))

# a rede salva a bola que ia cair
net_game = fresh()
net_game._fire_event(EVENT_SPECS["safety_net"])
net_game.balls = [Ball(position=pygame.Vector2(config.PLAYFIELD.centerx,
                                               config.PLAYFIELD.bottom - 20))]
net_game.balls[0].attached = False
net_game.balls[0].velocity = pygame.Vector2(0.0, 600.0)
for _ in range(30):
    net_game.advance(1 / 60, InputState())
check("the net bounces the ball back up",
      net_game.balls and net_game.balls[0].velocity.y < 0,
      f"{net_game.balls[0].velocity if net_game.balls else 'perdida'}")
check("the net costs no life", net_game.lives == config.START_LIVES)

dry = fresh()
dry.balls = [Ball(position=pygame.Vector2(config.PLAYFIELD.centerx,
                                          config.PLAYFIELD.bottom - 20))]
dry.balls[0].attached = False
dry.balls[0].velocity = pygame.Vector2(0.0, 600.0)
for _ in range(30):
    dry.advance(1 / 60, InputState())
check("without the net the same ball is lost", dry.lives == config.START_LIVES - 1,
      f"lives={dry.lives}")

# --- os sorteios sao independentes
first = Game(seed=99)
second = Game(seed=99)
for _ in range(40):
    first.events.force_next()
left = [first.modifiers.roll_drop(at_ball_cap=False) for _ in range(60)]
right = [second.modifiers.roll_drop(at_ball_cap=False) for _ in range(60)]
check("forcing events does not disturb the modifier sequence",
      [drop.spec.id if drop else None for drop in left]
      == [drop.spec.id if drop else None for drop in right])

# ============================================================ reta final ====
game = fresh()
check("the finale has not fired yet", not game._finale_fired)
check("the speed ramp starts at 1", abs(game.clear_ramp - 1.0) < 1e-9)

alive = [brick for brick in game.bricks if brick.alive]
while len(alive) > config.FINALE_BRICKS:
    brick = alive.pop()
    brick.hp = 0
    game.bricks_destroyed_level += 1

check("the speed ramp climbed with the cleared bricks",
      game.clear_ramp > 1.0, f"x{game.clear_ramp:.3f}")

game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("the finale fires when few bricks remain", game._finale_fired)
check("the finale hands out extra balls",
      len(game.balls) == config.FINALE_BALLS, f"{len(game.balls)}")
check("the finale announces itself",
      game._banner is not None and game._banner.text == "RETA FINAL")
check("the finale speeds the ball up",
      game.ball_speed > config.BALL_SPEED, f"{game.ball_speed:.0f} px/s")

before = len(game.balls)
game._fixed_step(config.FIXED_TIMESTEP, InputState())
check("the finale only fires once", len(game.balls) == before)

ramped = fresh()
check("a level with nothing destroyed has no ramp",
      abs(ramped.clear_ramp - 1.0) < 1e-9)
ramped.bricks_destroyed_level = ramped.bricks_total // 2
half = ramped.bricks_total // 2
expected = 1 + config.LEVEL_CLEAR_SPEED_RAMP * half / ramped.bricks_total
check("clearing half the grid is worth half the ramp",
      abs(ramped.clear_ramp - expected) < 1e-9, f"x{ramped.clear_ramp:.4f}")

cleared = fresh()
cleared.bricks_destroyed_level = cleared.bricks_total
check("a full ramp is the configured maximum",
      abs(cleared.clear_ramp - (1 + config.LEVEL_CLEAR_SPEED_RAMP)) < 1e-9,
      f"x{cleared.clear_ramp:.3f}")

# ======================================================== integracao ========
game = fresh(seed=2024)
play(game, 90.0)
check("a long run with events ends in a valid state",
      game.state in (State.PLAYING, State.GAME_OVER), f"{game.state}")
check("the ball speed invariant holds with every system on",
      all(abs(b.speed - game.ball_speed) < 1e-6 or b.attached for b in game.balls),
      f"{[round(b.speed) for b in game.balls]} alvo {game.ball_speed:.0f}")
check("particles never leak past the cap", len(game.vfx) <= config.PARTICLE_MAX,
      f"{len(game.vfx)}")
check("shake never exceeds the cap", game.shake <= config.SHAKE_MAX)
check("the banner always has time left",
      game._banner is None or game._banner.remaining > 0.0)
check("running events always have time left",
      all(event.remaining > 0.0 for event in game.events.running.values()))

# ============================================================ desenho =======
# Duas armadilhas aqui. O tremor desloca o mundo inteiro, entao as checagens de
# pixel o desligam. E o driver dummy devolve a MESMA superficie em set_mode, ou
# seja, dois Game simultaneos compartilham a tela — por isso os pixels sao
# amostrados imediatamente apos cada desenho, antes de criar o proximo jogo.
def sample(blackout=False):
    game = fresh(seed=4242)
    if blackout:
        game._fire_event(EVENT_SPECS["blackout"])
    game.shake = 0.0
    game.draw()
    brick = next(b for b in game.bricks if b.alive and b.row == 0)
    return {
        "far": game.screen.get_at((config.PLAYFIELD.left + 20,
                                   config.PLAYFIELD.top + 20))[:3],
        "brick": game.screen.get_at(brick.rect.center)[:3],
        "ball": game.screen.get_at((round(game.balls[0].position.x),
                                    round(game.balls[0].position.y)))[:3],
        "paddle": game.screen.get_at((game.paddle.rect.centerx,
                                      game.paddle.rect.centery))[:3],
    }


dark = sample(blackout=True)
plain = sample()

check("APAGAO collapses the far corner to the void colour",
      dark["far"] == config.COLOR_BLACKOUT, f"{dark['far']}")
check("APAGAO hides the bricks completely, not almost",
      dark["brick"] == config.COLOR_BLACKOUT,
      f"com apagao {dark['brick']}, sem apagao {plain['brick']}")
check("without APAGAO the same brick is clearly visible",
      sum(plain["brick"]) > 150, f"{plain['brick']}")
check("APAGAO leaves the ball lit exactly as before",
      dark["ball"] == plain["ball"], f"{dark['ball']} vs {plain['ball']}")
check("APAGAO leaves the paddle lit exactly as before",
      dark["paddle"] == plain["paddle"], f"{dark['paddle']} vs {plain['paddle']}")

game = fresh()
game._fire_event(EVENT_SPECS["safety_net"])
game.shake = 0.0
game.draw()
net_pixel = game.screen.get_at((config.PLAYFIELD.centerx,
                                config.PLAYFIELD.bottom - 4))[:3]
check("the safety net is drawn across the base",
      net_pixel == config.COLOR_SAFETY_NET, f"{net_pixel}")

game = fresh()
game._fire_event(EVENT_SPECS["capsule_rain"])
check("the event banner renders", game._banner is not None)

game = fresh()
game._damage_brick(next(b for b in game.bricks if b.alive and b.max_hp == 1))
check("breaking a brick spawns particles", len(game.vfx) > 0, f"{len(game.vfx)}")
check("breaking a brick spawns a floating score", len(game.popups) > 0,
      f"{len(game.popups)}")
game.draw()
check("particles render onto the world surface", len(game.vfx) > 0)

# ponta a ponta: a particula tem que aparecer no quadro final, nao so na superficie
spot = (config.PLAYFIELD.centerx, config.PLAYFIELD.top + 300)
spot_game = fresh()
spot_game.vfx.clear()
spot_game.vfx.burst(spot, (255, 0, 0), 20, 0.0, 2.0)
spot_game.shake = 0.0
spot_game.draw()
painted = any(
    spot_game.screen.get_at((spot[0] + dx, spot[1] + dy))[:3] == (255, 0, 0)
    for dx in range(-3, 4)
    for dy in range(-3, 4)
)
check("particles reach the frame the player sees", painted)

game.shutdown()
sys.exit(finish("dinâmica: partículas, sequência e eventos"))
