"""A bola: estado, integracao de posicao e desenho."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from src import config


@dataclass
class Ball:
    """Corpo circular que se move em velocidade constante.

    A posicao e o centro da bola. Enquanto ``attached`` for verdadeiro a bola
    fica presa na raquete esperando o lancamento, o que da ao jogador tempo
    para se posicionar.
    """

    position: pygame.Vector2
    velocity: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0.0, 0.0))
    radius: float = config.BALL_RADIUS
    attached: bool = True

    @classmethod
    def resting_on(cls, paddle) -> "Ball":
        return cls(
            position=pygame.Vector2(
                paddle.center_x,
                paddle.rect.top - config.BALL_RADIUS - config.COLLISION_SKIN,
            )
        )

    @property
    def rect(self) -> pygame.Rect:
        size = int(self.radius * 2)
        return pygame.Rect(
            int(self.position.x - self.radius),
            int(self.position.y - self.radius),
            size,
            size,
        )

    @property
    def speed(self) -> float:
        return self.velocity.length()

    def snap_to_paddle(self, paddle) -> None:
        self.position.update(
            paddle.center_x,
            paddle.rect.top - self.radius - config.COLLISION_SKIN,
        )
        self.velocity.update(0.0, 0.0)

    def launch(self, speed: float, angle_deg: float = 0.0) -> None:
        radians = math.radians(angle_deg)
        direction = pygame.Vector2(math.sin(radians), -math.cos(radians))
        self.velocity = direction * speed
        self.attached = False

    def advance(self, dt: float) -> None:
        self.position += self.velocity * dt

    def is_lost(self) -> bool:
        return self.position.y - self.radius > config.PLAYFIELD.bottom

    def draw(self, surface: pygame.Surface,
             sprite: pygame.Surface | None = None) -> None:
        center = (round(self.position.x), round(self.position.y))
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=center))
            return

        pygame.draw.circle(surface, config.COLOR_BALL, center, int(round(self.radius)))
        highlight_radius = max(2, int(round(self.radius * 0.34)))
        pygame.draw.circle(
            surface,
            config.COLOR_BALL_CORE,
            (center[0] - 2, center[1] - 3),
            highlight_radius,
        )
