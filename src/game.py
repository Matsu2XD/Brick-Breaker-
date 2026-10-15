"""Orquestracao do jogo: estados, passo fixo de simulacao, pontuacao e desenho."""

from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass

import pygame

from src import config, controls, physics
from src.audio import SoundBank
from src.entities.ball import Ball
from src.entities.brick import Brick
from src.entities.invader import Invader
from src.entities.paddle import Paddle
from src.entities.particle import ParticleSystem
from src.entities.popup import PopupSystem
from src.entities.projectile import Projectile
from src.events import EventDirector, EventSpec, Mood, mood_color
from src.level import build_bricks
from src.menu import Kind, Menu, Screen
from src.modifiers import specs
from src.modifiers.capsule import Capsule
from src.modifiers.manager import ModifierManager
from src.modifiers.specs import Drop, ModifierSpec, Polarity
from src.scores import Leaderboard
from src.settings import Settings
from src.sprites import SpriteSheet


class State(enum.Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    LEVEL_CLEAR = "level_clear"
    GAME_OVER = "game_over"


HUD_HINT = "A/D mover  |  S precisao  |  W lancar/atirar"

MENU_KEYS = "W/S: escolher    A/D: ajustar    ENTER: confirmar    ESC: voltar"

CONTROL_LINES = [
    "A/D ou setas: mover      S ou baixo: precisao",
    "W ou cima ou espaco: lancar e atirar",
    "M: som    P ou ESC: pausa    R: reiniciar",
    "",
    "Estrela: pontos    Coracoes: vidas    SEQUENCIA: acertos seguidos",
]

# Um atalho de teste por modificador do catalogo, na ordem de specs.MODIFIERS.
DEBUG_KEYS: dict[int, int] = {
    getattr(pygame, f"K_{index + 1}"): index for index in range(len(specs.MODIFIERS))
}


@dataclass
class Banner:
    """Aviso grande e temporario no alto do campo."""

    text: str
    color: tuple[int, int, int]
    remaining: float
    total: float


class Game:
    def __init__(self, seed: int | None = None) -> None:
        pygame.mixer.pre_init(config.SOUND_SAMPLE_RATE, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        )
        self.world = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_hud = pygame.font.Font(None, config.FONT_HUD)
        self.font_small = pygame.font.Font(None, config.FONT_SMALL)
        self.font_chip = pygame.font.Font(None, config.FONT_CHIP)
        self.font_capsule = pygame.font.Font(None, config.FONT_CAPSULE)
        self.font_title = pygame.font.Font(None, config.FONT_TITLE)
        self.font_popup = pygame.font.Font(None, config.POPUP_FONT)
        self.background = self._build_background()

        # Ajustes e placar vem do disco antes de tudo: eles decidem volume,
        # particulas e tremor, entao precisam existir antes do primeiro som.
        self.settings = Settings.load()
        self.leaderboard = Leaderboard.load()
        self.menu = Menu(settings=self.settings)
        self.audio = SoundBank()
        self._apply_settings()
        self.audio.start_music()

        # Sprites: quando o pack nao existe, tudo cai no desenho por primitiva.
        self.sprites = SpriteSheet()
        self.sprites.load()
        self.ball_sprite = self.sprites.ball(int(config.BALL_RADIUS * 2) + 4)
        self.heart_sprite = self.sprites.heart()
        self.star_sprite = self.sprites.star()

        # Superficies reaproveitadas pelo apagao (evita alocar por quadro).
        self._veil = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self._lit = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        # Cada sistema com aleatoriedade tem seu proprio gerador, para que o
        # sorteio de um nao desloque a sequencia do outro.
        self.rng = random.Random(seed)
        self.modifiers = ModifierManager(rng=self.rng)
        self.events = EventDirector(
            rng=random.Random(None if seed is None else seed + 1)
        )
        self.vfx = ParticleSystem(random.Random(0))
        self.popups = PopupSystem()

        self.accumulator = 0.0
        self.running = True
        self.state = State.MENU
        self.paddle = Paddle()
        self.bricks: list[Brick] = []
        self.balls: list[Ball] = []
        self.capsules: list[Capsule] = []
        self.projectiles: list[Projectile] = []
        self.invaders: list[Invader] = []
        self.score = 0
        self.lives = config.START_LIVES
        self.level = 1
        self.streak = 0
        self.bricks_total = 0
        self.bricks_destroyed_level = 0
        self.gun_cooldown = 0.0
        self.invader_spawn_timer = config.INVADER_SPAWN_INTERVAL
        self.muted = False
        self.shake = 0.0
        self.shake_phase = 0.0
        self._banner: Banner | None = None
        self._finale_fired = False
        self._final_position = 0
        self._launch_requested = False
        self._serve_angle = config.BALL_SERVE_ANGLE_DEG
        self._debug_factor_index = -1

        self.start_new_game()

        # Depois de start_new_game, porque preparar a fase deixa o jogo em
        # PLAYING: a primeira coisa que o jogador ve e a tela inicial.
        self.state = State.MENU

    # ---------------------------------------------------------------- loop --
    def run(self) -> None:
        while self.running:
            frame_time = self.clock.tick(config.FPS) / 1000.0
            self.handle_events()
            self.advance(frame_time, controls.InputState.from_keyboard())
            self.draw()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

    def _handle_keydown(self, key: int) -> None:
        # MENU e PAUSED compartilham o mesmo navegador; o resto do jogo tem teclas
        # proprias. A separacao evita que "S" signifique "descer no menu" e
        # "precisao" ao mesmo tempo.
        if self.state in (State.MENU, State.PAUSED):
            self._handle_menu_key(key)
            return

        if key == pygame.K_ESCAPE:
            if self.state in (State.GAME_OVER, State.LEVEL_CLEAR):
                self._to_main_menu()
            else:
                self._toggle_pause()
        elif key == pygame.K_p:
            self._toggle_pause()
        elif key == pygame.K_r:
            self.start_new_game()
        elif key == pygame.K_m:
            self.muted = self.audio.toggle_mute()
        elif key in controls.LAUNCH_KEYS:
            self._handle_launch_key()
        elif self.settings.debug_keys and key == pygame.K_e:
            self._fire_event(self.events.force_next())
        elif self.settings.debug_keys and key == pygame.K_0:
            self._debug_clear()
        elif self.settings.debug_keys and key in DEBUG_KEYS:
            self._debug_spawn(specs.MODIFIERS[DEBUG_KEYS[key]])

    # ---------------------------------------------------------------- menu --
    def _handle_menu_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w):
            self.menu.move(-1)
            self.audio.play("menu")
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu.move(1)
            self.audio.play("menu")
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.menu.adjust(-1)
            self._apply_settings()
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.menu.adjust(1)
            self._apply_settings()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.menu.screen is Screen.SCORES:
                self._leave_panel()
                return
            action = self.menu.activate()
            self.audio.play("menu")
            self._apply_settings()
            if action:
                self._run_menu_action(action)
        elif key == pygame.K_ESCAPE:
            self._menu_escape()

    def _menu_escape(self) -> None:
        if self.menu.screen in (Screen.SETTINGS, Screen.SCORES):
            self._leave_panel()
        elif self.state is State.PAUSED:
            self._resume()
        else:
            self.running = False

    def _run_menu_action(self, action: str) -> None:
        if action == "play":
            self.start_new_game()
        elif action == "scores":
            self.menu.open(Screen.SCORES)
        elif action == "settings":
            self.menu.open(Screen.SETTINGS)
        elif action == "resume":
            self._resume()
        elif action == "restart":
            self.start_new_game()
        elif action == "main":
            self._to_main_menu()
        elif action == "quit":
            self.running = False
        elif action == "back":
            self._leave_panel()

    def _leave_panel(self) -> None:
        if self.menu.screen is Screen.SETTINGS:
            self.settings.save()
        self.menu.back()

    def _resume(self) -> None:
        self.menu.screen = Screen.PAUSED
        self.state = State.PLAYING
        self.accumulator = 0.0

    def _to_main_menu(self) -> None:
        self.start_new_game()
        self.menu.open(Screen.MAIN)
        self.state = State.MENU

    def _toggle_pause(self) -> None:
        if self.state is State.PLAYING:
            self.menu.screen = Screen.PAUSED
            self.menu.cursor = 0
            self.state = State.PAUSED
        elif self.state is State.PAUSED:
            self._resume()

    def _handle_launch_key(self) -> None:
        if self.state is State.PLAYING:
            self._launch_requested = True
        elif self.state is State.LEVEL_CLEAR:
            self.level += 1
            self.reset_level()
        elif self.state is State.GAME_OVER:
            self.start_new_game()

    # ----------------------------------------------------------- partidas --
    def start_new_game(self) -> None:
        self.score = 0
        self.lives = config.START_LIVES
        self.level = 1
        self._final_position = 0
        self.modifiers.reset()
        self.reset_level()

    def reset_level(self) -> None:
        self.bricks = build_bricks(config.PLAYFIELD, self.sprites)
        self.bricks_total = len(self.bricks)
        self.bricks_destroyed_level = 0
        self._finale_fired = False
        self.streak = 0
        self.paddle.reset()
        self.balls = [Ball.resting_on(self.paddle)]
        self.capsules.clear()
        self.projectiles.clear()
        self.invaders.clear()
        self.vfx.clear()
        self.popups.clear()
        self.events.clear()
        self._banner = None
        self.shake = 0.0
        self.gun_cooldown = 0.0
        self.invader_spawn_timer = config.INVADER_SPAWN_INTERVAL
        self.modifiers.on_level_start()
        self._launch_requested = False
        self.accumulator = 0.0
        self.state = State.PLAYING

    @property
    def ball_speed(self) -> float:
        base = config.BALL_SPEED * (1.0 + config.LEVEL_SPEED_STEP * (self.level - 1))
        base *= self.clear_ramp
        base *= self.modifiers.ball_speed_multiplier
        base *= self.events.ball_speed_multiplier
        if self._finale_fired:
            base *= 1.0 + config.FINALE_SPEED_BONUS
        return base

    @property
    def clear_ramp(self) -> float:
        """Acelera a bola conforme a grade esvazia.

        Com poucos tijolos a bola passa a maior parte do tempo viajando, e a
        fase vira uma espera. Subir a velocidade no fim encurta as viagens e
        transforma a reta final na parte mais intensa em vez da mais chata.
        """
        if not self.bricks_total:
            return 1.0
        fraction = self.bricks_destroyed_level / self.bricks_total
        return 1.0 + config.LEVEL_CLEAR_SPEED_RAMP * fraction

    @property
    def streak_bonus(self) -> float:
        return 1.0 + min(self.streak, config.STREAK_BONUS_CAP) * config.STREAK_BONUS_STEP

    @property
    def gun_ready(self) -> bool:
        return self.modifiers.gun_active or self.events.is_running("free_gun")

    def next_serve_angle(self) -> float:
        """Alterna a inclinacao do lancamento.

        Sem essa inclinacao uma bola solta reta sobe e desce para sempre pela
        mesma coluna de tijolos. O sinal alternado troca a coluna a cada saque
        sem precisar de aleatoriedade, o que mantem a simulacao reproduzivel.
        """
        self._serve_angle = -self._serve_angle
        return self._serve_angle

    # ---------------------------------------------------------- simulacao --
    def advance(self, frame_time: float, input_state: controls.InputState) -> None:
        self.accumulator += min(frame_time, config.MAX_FRAME_TIME)
        if self.state is not State.PLAYING:
            self.accumulator = 0.0
            return

        while self.accumulator >= config.FIXED_TIMESTEP:
            self._fixed_step(config.FIXED_TIMESTEP, input_state)
            self.accumulator -= config.FIXED_TIMESTEP
            if self.state is not State.PLAYING:
                self.accumulator = 0.0
                return

    def _fixed_step(self, dt: float, input_state: controls.InputState) -> None:
        self._tick_feedback(dt)
        self.vfx.update(dt)
        self.popups.update(dt)
        self.modifiers.update(dt)

        spec = self.events.update(dt)
        if spec is not None:
            self._fire_event(spec)

        direction = input_state.move
        if self.modifiers.controls_inverted:
            direction = -direction
        self.paddle.move(dt, direction, input_state.precision)
        self.paddle.set_width_multiplier(self.modifiers.paddle_width_multiplier)

        self._update_balls(dt)
        self._update_gun(dt, input_state)
        self._update_projectiles(dt)
        self._update_capsules(dt)
        if self._update_invaders(dt):
            return

        self._enforce_ball_speed()
        self._launch_requested = False

        self.balls = [ball for ball in self.balls if not ball.is_lost()]
        if not self.balls:
            self._lose_life()
            return

        if all(not brick.alive for brick in self.bricks):
            self.state = State.LEVEL_CLEAR
            self.audio.play("level_complete")
        else:
            self._check_finale()

    # ---------------------------------------------------------- impacto ----
    def _tick_feedback(self, dt: float) -> None:
        self.shake_phase += dt
        self.shake = max(0.0, self.shake - config.SHAKE_DECAY * dt)
        if self._banner is not None:
            self._banner.remaining -= dt
            if self._banner.remaining <= 0.0:
                self._banner = None

    def _add_shake(self, amount: float) -> None:
        if not self.settings.screen_shake:
            return
        self.shake = min(config.SHAKE_MAX, max(self.shake, amount))

    def _burst(self, position, color, count: int, speed: float, life: float,
               direction=None, spread_deg: float = 62.0) -> None:
        """Solta particulas, respeitando o ajuste de performance."""
        if not self.settings.particles:
            return
        self.vfx.burst(position, color, count, speed, life, direction, spread_deg)

    def _apply_settings(self) -> None:
        """Empurra os ajustes para quem os consome.

        Volume e liga/desliga vao para o banco de sons. Particulas, tremor e
        teclas de teste sao consultados no momento do uso, entao nao precisam
        ser propagados: mudar o ajuste ja vale no proximo quadro.
        """
        self.audio.set_sfx_enabled(self.settings.sfx_enabled)
        self.audio.set_sfx_level(self.settings.sfx_volume)
        self.audio.set_music_level(self.settings.music_volume)
        self.audio.set_music_enabled(self.settings.music_enabled)

    @property
    def shake_offset(self) -> tuple[int, int]:
        """Deslocamento do mundo. Duas frequencias, sem consumir aleatoriedade."""
        if self.shake <= 0.15:
            return (0, 0)
        return (
            int(math.sin(self.shake_phase * 61.0) * self.shake),
            int(math.cos(self.shake_phase * 47.0) * self.shake),
        )

    def _show_banner(self, text: str, color: tuple[int, int, int]) -> None:
        self._banner = Banner(text, color, config.EVENT_BANNER_TIME,
                              config.EVENT_BANNER_TIME)

    # --------------------------------------------------------------- bola --
    def _enforce_ball_speed(self) -> None:
        """Mantem toda bola na velocidade efetiva do momento.

        Roda **no fim** do passo, depois de tudo que pode mudar a velocidade
        alvo: modificadores coletados, tijolos destruidos (a rampa de fase) e
        eventos. Assim a velocidade observada entre dois passos e sempre
        exatamente a esperada.

        Durante o passo a bola move com a velocidade fixada no passo anterior.
        Como a velocidade so muda em eventos discretos, o atraso maximo e de
        1/120 s, e a alternativa (reaplicar depois de cada causa) deixaria a
        checagem da invariante dependendo de qual causa disparou.
        """
        target = self.ball_speed
        for ball in self.balls:
            if ball.attached:
                continue
            speed = ball.speed
            if speed < 1e-6:
                continue
            ball.velocity = ball.velocity * (target / speed)

    def _update_balls(self, dt: float) -> None:
        net = self.events.is_running("safety_net")
        for ball in self.balls:
            if ball.attached:
                if self._launch_requested:
                    ball.launch(self.ball_speed, self.next_serve_angle())
                    self.gun_cooldown = config.GUN_LAUNCH_GRACE
                else:
                    ball.snap_to_paddle(self.paddle)
                    continue

            report = physics.move_and_collide(
                ball, dt, self.paddle, self.bricks, floor=net
            )
            self._on_ball_impact(report, ball)
            self._apply_report(report)
            self._ball_hits_invaders(ball)

    def _on_ball_impact(self, report: physics.CollisionReport, ball: Ball) -> None:
        spark = config.COLOR_PARTICLE_SPARK
        if report.walls_hit:
            self.audio.play("wall")
            self._burst(ball.position, spark, config.PARTICLE_SPARK_COUNT,
                           config.PARTICLE_SPARK_SPEED, config.PARTICLE_SPARK_LIFE)
        if report.paddle_hits:
            self.audio.play("paddle")
            self._add_shake(config.SHAKE_PADDLE)
            self._burst(
                (ball.position.x, self.paddle.rect.top), spark,
                config.PARTICLE_SPARK_COUNT + 2, config.PARTICLE_SPARK_SPEED * 1.4,
                config.PARTICLE_SPARK_LIFE, direction=(0.0, -1.0), spread_deg=70.0,
            )
        if report.bricks_hit:
            self.audio.play("brick")

    def _apply_report(self, report: physics.CollisionReport) -> None:
        resolved: set[int] = set()
        for brick in report.bricks_hit:
            if id(brick) in resolved:
                continue
            resolved.add(id(brick))
            self._damage_brick(brick)

    def _damage_brick(self, brick: Brick) -> None:
        multiplier = self.modifiers.score_multiplier * self.streak_bonus
        if brick.damage():
            points = int(brick.score_value * multiplier)
            self.score += points
            self.popups.spawn(f"+{points}", brick.rect.center, self._points_color)
            self._on_brick_destroyed(brick)
        else:
            self.score += int(config.SCORE_PER_HIT * multiplier)
            self._burst(brick.rect.center, brick.color,
                           config.PARTICLE_SPARK_COUNT, config.PARTICLE_SPARK_SPEED,
                           config.PARTICLE_SPARK_LIFE)

    @property
    def _points_color(self) -> tuple[int, int, int]:
        """O placar flutuante muda de cor quando algum multiplicador esta ativo."""
        if self.modifiers.score_multiplier * self.streak_bonus > 1.1:
            return config.COLOR_STREAK_HOT
        return config.COLOR_TEXT

    def _on_brick_destroyed(self, brick: Brick) -> None:
        self.streak += 1
        self.bricks_destroyed_level += 1
        self._burst(brick.rect.center, brick.color, config.PARTICLE_BRICK_COUNT,
                       config.PARTICLE_BRICK_SPEED, config.PARTICLE_BRICK_LIFE)
        self._add_shake(config.SHAKE_BRICK)

        if self.streak % config.STREAK_REWARD_STEP == 0:
            self._grant_streak_reward()

        drop = self.modifiers.roll_drop(at_ball_cap=len(self.balls) >= config.MAX_BALLS)
        if drop is None:
            return
        if len(self.capsules) >= config.CAPSULE_MAX_ON_SCREEN:
            return
        self.capsules.append(Capsule.falling_from(drop, brick.rect.center))

    def _grant_streak_reward(self) -> None:
        """A cada N tijolos seguidos, uma capsula garantida.

        Sem isso toda recompensa do jogo e sorteio e o jogador nao tem nenhum
        controle sobre a propria sorte. Com isso, ele pode ir atras.
        """
        drop = self.modifiers.force_drop(at_ball_cap=len(self.balls) >= config.MAX_BALLS)
        self._burst(
            (self.paddle.center_x, self.paddle.rect.top - 14),
            config.COLOR_CAPSULE_BUFF if drop.is_buff else config.COLOR_CAPSULE_DEBUFF,
            config.PARTICLE_BRICK_COUNT * 2, config.PARTICLE_BRICK_SPEED,
            config.PARTICLE_BRICK_LIFE,
        )
        self._add_shake(config.SHAKE_BRICK * 2)
        self._collect(drop)

    def _ball_hits_invaders(self, ball: Ball) -> None:
        for invader in self.invaders:
            if not invader.alive:
                continue
            contact = physics.circle_rect_contact(ball.position, ball.radius, invader.rect)
            if contact is None:
                continue
            normal, penetration = contact
            ball.position += normal * (penetration + config.COLLISION_SKIN)
            if ball.velocity.dot(normal) < 0.0:
                ball.velocity = physics.enforce_min_vertical(
                    ball.velocity.reflect(normal)
                )
            self._destroy_invader(invader)
            return

    def _multiply_balls(self, factor: int) -> None:
        self._grow_ball_count(min(config.MAX_BALLS, len(self.balls) * factor))

    def _grow_ball_count(self, target: int) -> None:
        target = min(config.MAX_BALLS, target)
        if target <= len(self.balls):
            return

        sources = [ball for ball in self.balls if not ball.attached] or list(self.balls)
        index = 0
        while len(self.balls) < target:
            source = sources[index % len(sources)]
            clone = Ball(
                position=source.position.copy(),
                velocity=source.velocity.copy(),
                attached=source.attached,
            )
            if clone.velocity.length_squared() > 1e-9:
                laps = index // len(sources) + 1
                side = 1.0 if index % 2 == 0 else -1.0
                clone.velocity = clone.velocity.rotate(
                    config.BALL_CLONE_SPREAD_DEG * laps * side
                )
                clone.velocity = clone.velocity * (self.ball_speed / clone.velocity.length())
            self.balls.append(clone)
            index += 1

    # ------------------------------------------------------------ capsule --
    def _update_capsules(self, dt: float) -> None:
        paddle_rect = self.paddle.rect
        for capsule in self.capsules:
            capsule.update(dt)
            if capsule.rect.colliderect(paddle_rect):
                capsule.collected = True
                self._collect(capsule.drop)
        self.capsules = [
            capsule
            for capsule in self.capsules
            if not capsule.collected and not capsule.is_lost()
        ]

    def _collect(self, drop: Drop) -> None:
        color = config.COLOR_CAPSULE_BUFF if drop.is_buff else config.COLOR_CAPSULE_DEBUFF
        self.audio.play("power_up" if drop.is_buff else "debuff")
        self.popups.spawn(self._drop_caption(drop),
                          (self.paddle.center_x, self.paddle.rect.top - 26), color)
        self._burst(
            (self.paddle.center_x, self.paddle.rect.top), color,
            config.PARTICLE_SPARK_COUNT + 3, config.PARTICLE_SPARK_SPEED * 1.6,
            config.PARTICLE_SPARK_LIFE,
            direction=(0.0, -1.0), spread_deg=90.0,
        )
        if drop.spec.id == "ball_multiplier":
            self._multiply_balls(drop.magnitude)
        self.modifiers.activate(drop)

    @staticmethod
    def _drop_caption(drop: Drop) -> str:
        """O nome que sobe na tela quando a capsula e capturada."""
        if drop.spec.id == "ball_multiplier":
            return f"{drop.magnitude} BOLAS"
        return drop.spec.hud

    # ------------------------------------------------------------ canhao ---
    def _update_gun(self, dt: float, input_state: controls.InputState) -> None:
        if self.gun_cooldown > 0.0:
            self.gun_cooldown -= dt

        free = self.events.is_running("free_gun")
        if not (self.gun_ready and input_state.action):
            return
        if any(ball.attached for ball in self.balls):
            return
        if self.gun_cooldown > 0.0:
            return
        if not free and not self.modifiers.consume_shot():
            return

        self.gun_cooldown = config.GUN_COOLDOWN
        muzzle = pygame.Vector2(
            self.paddle.center_x,
            self.paddle.rect.top - config.PROJECTILE_HEIGHT / 2.0,
        )
        self.projectiles.append(
            Projectile(
                position=muzzle,
                velocity=pygame.Vector2(0.0, -config.PROJECTILE_SPEED),
            )
        )
        self._burst(muzzle, config.COLOR_PARTICLE_SPARK,
                       config.PARTICLE_SPARK_COUNT // 2, config.PARTICLE_SPARK_SPEED,
                       config.PARTICLE_SPARK_LIFE)
        self.audio.play("shoot")

    def _update_projectiles(self, dt: float) -> None:
        for projectile in self.projectiles:
            projectile.update(dt)
            if projectile.is_off(config.PLAYFIELD):
                projectile.alive = False
                continue

            brick_hit = None
            for brick in self.bricks:
                if brick.alive and projectile.rect.colliderect(brick.rect):
                    brick_hit = brick
                    break
            if brick_hit is not None:
                projectile.alive = False
                self._damage_brick(brick_hit)
                self.audio.play("brick")
                continue

            for invader in self.invaders:
                if invader.alive and projectile.rect.colliderect(invader.rect):
                    projectile.alive = False
                    self._destroy_invader(invader)
                    break

        self.projectiles = [p for p in self.projectiles if p.alive]

    # ---------------------------------------------------------- invasores --
    def _update_invaders(self, dt: float) -> bool:
        """Devolve True quando um invasor acerta a bandeja e custa uma vida."""
        if self.modifiers.invaders_active:
            self.invader_spawn_timer -= dt
            if (
                self.invader_spawn_timer <= 0.0
                and len(self.invaders) < config.INVADER_MAX_ALIVE
            ):
                self.invader_spawn_timer = config.INVADER_SPAWN_INTERVAL
                self._spawn_invader()

        paddle_rect = self.paddle.rect
        hit_paddle = False
        for invader in self.invaders:
            if not invader.alive:
                continue
            invader.update(dt, config.PLAYFIELD)
            if invader.rect.colliderect(paddle_rect):
                invader.alive = False
                hit_paddle = True

        self.invaders = [
            invader
            for invader in self.invaders
            if invader.alive and not invader.is_off(config.PLAYFIELD)
        ]

        if hit_paddle:
            self._lose_life()
            return True
        return False

    def _spawn_invader(self) -> None:
        margin = config.INVADER_SPAWN_MARGIN
        x = self.rng.uniform(
            config.PLAYFIELD.left + margin, config.PLAYFIELD.right - margin
        )
        side = self.rng.choice((-1.0, 1.0))
        self.invaders.append(
            Invader(
                position=pygame.Vector2(x, config.PLAYFIELD.top + config.INVADER_HEIGHT),
                velocity=pygame.Vector2(
                    side * config.INVADER_SPEED_X, config.INVADER_SPEED_Y
                ),
            )
        )

    def _destroy_invader(self, invader: Invader) -> None:
        invader.alive = False
        self._burst(invader.position, config.COLOR_INVADER,
                       config.PARTICLE_BRICK_COUNT, config.PARTICLE_BRICK_SPEED,
                       config.PARTICLE_BRICK_LIFE)
        self._add_shake(config.SHAKE_BRICK)
        self.audio.play("invader")

    # ------------------------------------------------------------ eventos --
    def _fire_event(self, spec: EventSpec) -> None:
        """Registra o evento e aplica os efeitos. Entrada unica para disparar."""
        self.events.start(spec)
        self._show_banner(spec.name, mood_color(spec.mood))
        self.audio.play("power_up" if spec.mood is Mood.BOON else "debuff")
        self._add_shake(config.SHAKE_EVENT)

        if spec.id == "capsule_rain":
            self._rain_capsules()
        elif spec.id == "ball_frenzy":
            self._grow_ball_count(config.EVENT_FRENZY_BALLS)
        elif spec.id == "invasion":
            self._invade()

    def _rain_capsules(self) -> None:
        for index in range(config.EVENT_CAPSULE_RAIN_COUNT):
            if len(self.capsules) >= config.EVENT_CAPSULE_RAIN_MAX:
                return
            drop = self.modifiers.force_drop(
                at_ball_cap=len(self.balls) >= config.MAX_BALLS
            )
            x = self.rng.uniform(
                config.PLAYFIELD.left + 40, config.PLAYFIELD.right - 40
            )
            y = config.PLAYFIELD.top + 30 + index * 12
            self.capsules.append(Capsule.falling_from(drop, (int(x), int(y))))

    def _invade(self) -> None:
        for _ in range(config.EVENT_INVASION_COUNT):
            if len(self.invaders) >= config.EVENT_INVASION_MAX:
                return
            self._spawn_invader()

    def _check_finale(self) -> None:
        if self._finale_fired or not self.bricks_total:
            return
        alive = sum(1 for brick in self.bricks if brick.alive)
        if alive > config.FINALE_BRICKS:
            return

        self._finale_fired = True
        self._grow_ball_count(config.FINALE_BALLS)
        self._show_banner("RETA FINAL", config.COLOR_EVENT_BOON)
        self._add_shake(config.SHAKE_FINALE)
        self.audio.play("power_up")

    # --------------------------------------------------------------- vidas --
    def _lose_life(self) -> None:
        self.lives -= 1
        self.streak = 0
        self._add_shake(config.SHAKE_LIFE_LOST)
        self._burst(
            (self.paddle.center_x, self.paddle.rect.top), config.COLOR_DANGER,
            config.PARTICLE_BRICK_COUNT * 2, config.PARTICLE_BRICK_SPEED,
            config.PARTICLE_BRICK_LIFE,
        )
        self.capsules.clear()
        self.projectiles.clear()
        self.invaders.clear()
        self.gun_cooldown = 0.0
        self.modifiers.on_life_lost()

        if self.lives <= 0:
            self.lives = 0
            self.state = State.GAME_OVER
            self.audio.play("game_over")
            self._final_position = self.leaderboard.submit(self.score, self.level)
            return

        self.balls = [Ball.resting_on(self.paddle)]
        self._launch_requested = False
        self.audio.play("lose_ball")

    # --------------------------------------------------------- ferramentas --
    def _debug_spawn(self, spec: ModifierSpec) -> None:
        magnitude = 0
        if spec.id == "ball_multiplier":
            self._debug_factor_index = (self._debug_factor_index + 1) % len(
                config.BALL_MULTIPLIER_FACTORS
            )
            magnitude = config.BALL_MULTIPLIER_FACTORS[self._debug_factor_index]
        origin = (self.paddle.rect.centerx, self.paddle.rect.top - 70)
        self.capsules.append(
            Capsule.falling_from(Drop(spec=spec, magnitude=magnitude), origin)
        )

    def _debug_clear(self) -> None:
        self.modifiers.on_level_start()
        self.events.clear()
        self.capsules.clear()
        self.projectiles.clear()
        self.invaders.clear()
        self.vfx.clear()
        self.popups.clear()
        self._banner = None
        self.paddle.set_width_multiplier(1.0)

    # ------------------------------------------------------------ desenho --
    def draw(self) -> None:
        world = self.world
        world.blit(self.background, (0, 0))
        self._draw_walls(world)
        for brick in self.bricks:
            if brick.alive:
                brick.draw(world)
        for capsule in self.capsules:
            capsule.draw(world, self.font_capsule)
        for invader in self.invaders:
            invader.draw(world)
        for projectile in self.projectiles:
            projectile.draw(world)
        self._draw_safety_net(world)
        self.paddle.draw(world, show_gun=self.gun_ready)
        for ball in self.balls:
            ball.draw(world, self.ball_sprite)
        self.vfx.draw(world)
        self.popups.draw(world, self.font_popup)

        offset = self.shake_offset
        if offset != (0, 0):
            self.screen.fill(config.COLOR_GRADIENT_TOP)
        self.screen.blit(world, offset)

        if self.events.is_running("blackout"):
            self._draw_blackout()

        if self.state in (State.MENU, State.PAUSED):
            self._draw_menu()
            pygame.display.flip()
            return

        self._draw_hud()
        self._draw_banner()
        self._draw_overlay()
        pygame.display.flip()

    # ------------------------------------------------------------- menus ---
    def _draw_menu(self) -> None:
        if self.menu.screen is Screen.SCORES:
            self._draw_scoreboard()
            return

        if self.menu.screen is Screen.SETTINGS:
            rows = [(item.label, self.menu.value_text(item))
                    for item in self.menu.items]
            self._draw_panel("AJUSTES", rows, config.WINDOW_WIDTH // 2)
            return

        if self.menu.screen is Screen.PAUSED:
            rows = [(item.label, "") for item in self.menu.items]
            self._draw_panel("PAUSA", rows, config.WINDOW_WIDTH // 2)
            return

        rows = [(item.label, "") for item in self.menu.items]
        self._draw_panel(config.TITLE, rows, config.WINDOW_WIDTH // 4 + 40,
                         side=self._draw_menu_scores)

    def _draw_menu_scores(self, center_x: int, top: int) -> None:
        """Placar resumido ao lado do menu inicial."""
        entries = self.leaderboard.entries[:5]
        title = self.font_hud.render("RECORDES", True, config.COLOR_STREAK_HOT)
        self.screen.blit(title, (center_x - title.get_width() // 2, top))

        if not entries:
            empty = self.font_small.render("nenhum ainda", True, config.COLOR_MUTED)
            self.screen.blit(empty, (center_x - empty.get_width() // 2, top + 34))
            return

        for index, entry in enumerate(entries):
            line = f"{index + 1}. {entry.score:>6}  fase {entry.level}"
            color = config.COLOR_MENU_SELECTED if index == 0 else config.COLOR_TEXT
            text = self.font_small.render(line, True, color)
            self.screen.blit(text, (center_x - 90, top + 34 + index * 26))

    def _draw_panel(self, title: str, rows, center_x: int, side=None) -> None:
        """Painel central com titulo, itens e a marca do cursor."""
        veil = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
                              pygame.SRCALPHA)
        veil.fill(config.COLOR_MENU_VEIL)
        self.screen.blit(veil, (0, 0))

        heading = self.font_title.render(title, True, config.COLOR_TEXT)
        self.screen.blit(heading, (center_x - heading.get_width() // 2, 96))

        top = 200
        line_height = 34
        for index, (label, value) in enumerate(rows):
            selected = index == self.menu.cursor
            y = top + index * line_height
            color = config.COLOR_MENU_SELECTED if selected else config.COLOR_TEXT
            if selected:
                marker = self.font_hud.render(">", True, config.COLOR_MENU_SELECTED)
                self.screen.blit(marker, (center_x - 150, y))
            text = self.font_hud.render(label, True, color)
            self.screen.blit(text, (center_x - 128, y))
            if value:
                shown = self.font_hud.render(value, True, config.COLOR_MUTED)
                self.screen.blit(shown, (center_x + 70, y))

        if side is not None:
            side(config.WINDOW_WIDTH // 4 * 3 + 40, top)

        hint = self.font_small.render(MENU_KEYS, True, config.COLOR_MUTED)
        self.screen.blit(hint, (config.WINDOW_WIDTH // 2 - hint.get_width() // 2,
                                config.WINDOW_HEIGHT - 84))

    def _draw_scoreboard(self) -> None:
        veil = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
                              pygame.SRCALPHA)
        veil.fill(config.COLOR_MENU_VEIL)
        self.screen.blit(veil, (0, 0))

        centre = config.WINDOW_WIDTH // 2
        heading = self.font_title.render("PLACAR DE LIDERES", True, config.COLOR_TEXT)
        self.screen.blit(heading, (centre - heading.get_width() // 2, 96))

        if not self.leaderboard.entries:
            empty = self.font_hud.render("Nenhuma partida terminada ainda.",
                                         True, config.COLOR_MUTED)
            self.screen.blit(empty, (centre - empty.get_width() // 2, 220))
        for index, entry in enumerate(self.leaderboard.entries):
            y = 190 + index * 30
            position = self.font_hud.render(f"{index + 1}.", True,
                                            config.COLOR_MUTED)
            score = self.font_hud.render(f"{entry.score:>7}", True,
                                         config.COLOR_TEXT if index else
                                         config.COLOR_STREAK_HOT)
            detail = self.font_small.render(
                f"fase {entry.level}    {entry.date}", True, config.COLOR_MUTED)
            self.screen.blit(position, (centre - 210, y))
            self.screen.blit(score, (centre - 170, y))
            self.screen.blit(detail, (centre + 30, y + 4))

        hint = self.font_small.render("ESC ou ENTER volta", True, config.COLOR_MUTED)
        self.screen.blit(hint, (centre - hint.get_width() // 2,
                                config.WINDOW_HEIGHT - 96))

    def _build_background(self) -> pygame.Surface:
        top = config.COLOR_GRADIENT_TOP
        bottom = config.COLOR_GRADIENT_BOTTOM
        height = config.WINDOW_HEIGHT
        surface = pygame.Surface((config.WINDOW_WIDTH, height))
        for y in range(height):
            ratio = y / (height - 1)
            color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
            pygame.draw.line(surface, color, (0, y), (config.WINDOW_WIDTH, y))
        return surface

    def _draw_walls(self, surface: pygame.Surface) -> None:
        field_rect = config.PLAYFIELD
        thickness = config.WALL_THICKNESS
        top = pygame.Rect(
            field_rect.left - thickness,
            field_rect.top - thickness,
            field_rect.width + thickness * 2,
            thickness,
        )
        left = pygame.Rect(field_rect.left - thickness, field_rect.top, thickness, field_rect.height)
        right = pygame.Rect(field_rect.right, field_rect.top, thickness, field_rect.height)
        for wall in (top, left, right):
            pygame.draw.rect(surface, config.COLOR_WALL, wall)

        kill_line = pygame.Rect(field_rect.left, field_rect.bottom - 2, field_rect.width, 2)
        pygame.draw.rect(surface, config.COLOR_DANGER, kill_line)

    def _draw_safety_net(self, surface: pygame.Surface) -> None:
        if not self.events.is_running("safety_net"):
            return
        field_rect = config.PLAYFIELD
        band = pygame.Rect(field_rect.left, field_rect.bottom - 6, field_rect.width, 5)
        pygame.draw.rect(surface, config.COLOR_SAFETY_NET, band)
        pygame.draw.rect(surface, config.COLOR_BALL_CORE,
                         pygame.Rect(band.left, band.top + 1, band.width, 1))

    def _draw_blackout(self) -> None:
        """Escurece o campo e ilumina so em volta da bandeja e das bolas.

        Fazer isso com uma veu translucido sobre a tela **nao funciona**: por mais
        opaco que seja, sobra luz suficiente para os tijolos continuarem nitidos.
        Aqui o mundo e *mascarado* em vez de coberto — o que fica fora do circulo
        de luz vira preto de verdade, e nao "quase preto".

        A mascara e uma superficie em tons de cinza com circulos concentricos: o
        centro e branco (255, deixa passar) e a borda e preto (0, apaga). Depois
        o mundo e multiplicado por ela (BLEND_RGB_MULT). Ordenar os circulos do
        maior para o menor garante que o centro, desenhado por ultimo, ganhe.
        """
        mask = self._veil
        mask.fill((0, 0, 0))

        lights = [(int(self.paddle.center_x), self.paddle.rect.centery,
                   config.EVENT_BLACKOUT_RADIUS_PADDLE)]
        lights += [(int(ball.position.x), int(ball.position.y),
                    config.EVENT_BLACKOUT_RADIUS_BALL) for ball in self.balls]

        steps = max(2, config.EVENT_BLACKOUT_BANDS)
        bands = []
        for cx, cy, radius in lights:
            for step in range(steps):
                value = int(255 * (1.0 - step / (steps - 1)))
                bands.append((radius + step * config.EVENT_BLACKOUT_BAND, value, cx, cy))

        for radius, value, cx, cy in sorted(bands, key=lambda band: -band[0]):
            pygame.draw.circle(mask, (value, value, value), (cx, cy), radius)

        lit = self._lit
        lit.blit(self.world, (0, 0))
        lit.blit(mask, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        # `lit` cobre a tela inteira e ja traz o preto fora da luz, entao nao ha
        # o que preencher antes: a area escura e literalmente (0, 0, 0).
        self.screen.blit(lit, (0, 0))

    def _draw_hud(self) -> None:
        pygame.draw.rect(
            self.screen,
            config.COLOR_HUD,
            pygame.Rect(0, 0, config.WINDOW_WIDTH, config.HUD_HEIGHT),
        )
        row_one = 20
        row_two = 58

        self._draw_score(row_one)
        self._draw_lives(row_one)
        for x, color, label in (
            (272, config.COLOR_TEXT, f"NIVEL {self.level}"),
            (382, config.COLOR_TEXT, f"BOLAS {len(self.balls)}"),
            (496, self.streak_color, f"SEQUENCIA {self.streak}"),
        ):
            surface = self.font_hud.render(label, True, color)
            self.screen.blit(surface, (x, row_one - surface.get_height() // 2))

        hint = self.font_small.render(HUD_HINT, True, config.COLOR_MUTED)
        self.screen.blit(
            hint,
            (config.WINDOW_WIDTH - hint.get_width() - 16,
             row_one - hint.get_height() // 2),
        )

        summary = self._summary_text()
        summary_width = (
            self.font_chip.size(summary)[0] + 16 if summary else 0
        )
        self._draw_effect_chips(row_two, summary_width)
        self._draw_active_summary(row_two, summary)

    def _draw_score(self, center_y: int) -> None:
        """Estrela + numero. O icone substitui a palavra PONTOS."""
        x = 16
        if self.star_sprite is not None:
            self.screen.blit(self.star_sprite,
                             self.star_sprite.get_rect(centery=center_y, left=x))
            x += self.star_sprite.get_width() + 8
        score = self.font_hud.render(f"{self.score:06d}", True, config.COLOR_TEXT)
        self.screen.blit(score, (x, center_y - score.get_height() // 2))

    def _draw_lives(self, center_y: int) -> None:
        """Um coracao por vida — a leitura mais rapida possivel."""
        x = 170
        if self.heart_sprite is None:
            surface = self.font_hud.render(f"VIDAS {self.lives}", True, config.COLOR_TEXT)
            self.screen.blit(surface, (x, center_y - surface.get_height() // 2))
            return
        for _ in range(max(0, self.lives)):
            self.screen.blit(self.heart_sprite,
                             self.heart_sprite.get_rect(centery=center_y, left=x))
            x += self.heart_sprite.get_width() + 4

    @property
    def streak_color(self) -> tuple[int, int, int]:
        if self.streak >= config.STREAK_FIRE:
            return config.COLOR_STREAK_FIRE
        if self.streak >= config.STREAK_HOT:
            return config.COLOR_STREAK_HOT
        return config.COLOR_STREAK

    def _summary_text(self) -> str:
        parts: list[str] = []
        if self.modifiers.score_stacks:
            parts.append(f"PONTOS x{int(self.modifiers.score_multiplier)}")
        if self.modifiers.gun_shots:
            parts.append(f"TIROS {self.modifiers.gun_shots}")
        if self.audio.muted:
            parts.append("MUDO")
        return "     ".join(parts)

    def _draw_effect_chips(self, center_y: int, reserved: int) -> None:
        """Um chip por efeito ativo. Enche da esquerda para a direita e para.

        O limite existe porque modificadores e eventos somam: sem ele, uma pilha
        cheia empurraria os chips por cima do resumo da direita.
        """
        limit = config.WINDOW_WIDTH - 16 - (reserved + 20 if reserved else 0)
        x = 16
        height = 24
        hidden = 0

        labels: list[tuple[str, tuple[int, int, int], bool]] = []
        for effect in self.modifiers.timed_effects():
            label = effect.spec.hud
            if effect.stacks > 1:
                label = f"{label} x{effect.stacks}"
            color = (
                config.COLOR_CHIP_BUFF
                if effect.spec.polarity is Polarity.BUFF
                else config.COLOR_CHIP_DEBUFF
            )
            labels.append((f"{label}  {max(0.0, effect.remaining):.0f}s", color, True))
        for event in self.events.running.values():
            labels.append(
                (f"{event.spec.chip}  {max(0.0, event.remaining):.0f}s",
                 mood_color(event.spec.mood), False)
            )

        for label, color, filled in labels:
            text = self.font_chip.render(label, True, config.COLOR_CHIP_TEXT)
            width = text.get_width() + 18
            if x + width > limit:
                hidden += 1
                continue

            rect = pygame.Rect(x, center_y - height // 2, width, height)
            if filled:
                pygame.draw.rect(self.screen, color, rect, border_radius=7)
            else:
                pygame.draw.rect(self.screen, color, rect, width=2, border_radius=7)
            self.screen.blit(text, text.get_rect(center=rect.center))
            x += width + 8

        if hidden:
            more = self.font_chip.render(f"+{hidden}", True, config.COLOR_MUTED)
            self.screen.blit(more, (x, center_y - more.get_height() // 2))

    def _draw_active_summary(self, center_y: int, summary: str) -> None:
        if not summary:
            return
        text = self.font_chip.render(summary, True, config.COLOR_GUN)
        self.screen.blit(
            text,
            (config.WINDOW_WIDTH - text.get_width() - 16,
             center_y - text.get_height() // 2),
        )

    def _draw_banner(self) -> None:
        if self._banner is None:
            return

        progress = 1.0 - self._banner.remaining / self._banner.total
        if progress < 0.18:
            alpha = progress / 0.18
        elif progress > 0.7:
            alpha = max(0.0, (1.0 - progress) / 0.3)
        else:
            alpha = 1.0

        shadow = self.font_title.render(self._banner.text, True, (8, 10, 20))
        shadow.set_alpha(int(190 * alpha))
        text = self.font_title.render(self._banner.text, True, self._banner.color)
        text.set_alpha(int(255 * alpha))

        x = config.WINDOW_WIDTH // 2 - text.get_width() // 2
        y = config.PLAYFIELD.top + 72
        self.screen.blit(shadow, (x + 3, y + 3))
        self.screen.blit(text, (x, y))

    def _draw_overlay(self) -> None:
        """Telas de fim de fase e de fim de jogo.

        A pausa nao passa por aqui: ela e um menu de verdade (``State.PAUSED``),
        com itens navegaveis, e nao um aviso.
        """
        if self.state is State.LEVEL_CLEAR:
            title = f"NIVEL {self.level} LIMPO"
            lines = [(f"Pontuacao: {self.score}", config.COLOR_TEXT),
                     ("W para o proximo nivel", config.COLOR_MUTED),
                     ("ESC volta ao menu", config.COLOR_MUTED)]
        elif self.state is State.GAME_OVER:
            title = "FIM DE JOGO"
            lines = [(f"Pontuacao final: {self.score}", config.COLOR_TEXT)]
            if self._final_position:
                lines.append((f"NOVO RECORDE — {self._final_position}o lugar",
                              config.COLOR_MENU_SELECTED))
            else:
                lines.append((f"Melhor ate agora: {self.leaderboard.best}",
                              config.COLOR_MUTED))
            lines.append(("W joga de novo    ESC volta ao menu", config.COLOR_MUTED))
        else:
            return

        veil = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        veil.fill(config.COLOR_OVERLAY)
        self.screen.blit(veil, (0, 0))

        centre = config.PLAYFIELD.center
        title_surface = self.font_title.render(title, True, config.COLOR_TEXT)
        self.screen.blit(
            title_surface,
            (centre[0] - title_surface.get_width() // 2, centre[1] - 130),
        )

        for index, (line, color) in enumerate(lines):
            line_surface = self.font_small.render(line, True, color)
            self.screen.blit(
                line_surface,
                (centre[0] - line_surface.get_width() // 2,
                 centre[1] - 44 + index * 28),
            )

        if self.state is State.GAME_OVER:
            self._draw_leaderboard_strip(centre[0], centre[1] + 52)

    def _draw_leaderboard_strip(self, center_x: int, top: int) -> None:
        """As cinco melhores logo abaixo do fim de jogo, para comparar de imediato."""
        entries = self.leaderboard.entries[:5]
        if not entries:
            return
        heading = self.font_small.render("MELHORES", True, config.COLOR_STREAK_HOT)
        self.screen.blit(heading, (center_x - heading.get_width() // 2, top))
        for index, entry in enumerate(entries):
            line = f"{index + 1}. {entry.score:>6}  fase {entry.level}"
            color = config.COLOR_MENU_SELECTED if index == 0 else config.COLOR_MUTED
            text = self.font_small.render(line, True, color)
            self.screen.blit(text, (center_x - text.get_width() // 2,
                                    top + 26 + index * 24))

    def shutdown(self) -> None:
        """Grava ajustes e placar antes de fechar.

        O placar ja e gravado a cada envio; os ajustes sao gravados ao sair da
        tela de ajustes, e aqui de novo por garantia: se o jogador mudou algo e
        fechou a janela direto, a mudanca nao pode se perder.
        """
        self.settings.save()
        self.audio.stop_music()
        pygame.quit()
