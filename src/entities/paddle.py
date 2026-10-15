"""A bandeja controlada pelo jogador."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from src import config


@dataclass
class Paddle:
    """Caixa alinhada aos eixos que se move apenas na horizontal.

    ``position`` e o canto superior esquerdo em espaco continuo (float) e
    ``velocity_x`` e mantida para que a bola herde o "english" da bandeja em
    movimento. ``width`` e mutavel porque o modificador Bandeja Grande a
    redimensiona em tempo de execucao.
    """

    position: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0.0, 0.0))
    velocity_x: float = 0.0
    width: float = config.PADDLE_WIDTH
    height: float = config.PADDLE_HEIGHT

    def __post_init__(self) -> None:
        self.reset()

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.position.x),
            int(self.position.y),
            int(self.width),
            int(self.height),
        )

    @property
    def center_x(self) -> float:
        return self.position.x + self.width / 2.0

    def reset(self) -> None:
        field_rect = config.PLAYFIELD
        self.width = config.PADDLE_WIDTH
        self.position.update(
            field_rect.centerx - self.width / 2.0,
            field_rect.bottom - config.PADDLE_BOTTOM_MARGIN - self.height,
        )
        self.velocity_x = 0.0

    def set_width_multiplier(self, multiplier: float) -> None:
        """Redimensiona mantendo o centro.

        Redimensionar pelo centro e o que impede a bandeja de escorregar para
        fora da mao do jogador quando o modificador comeca ou termina.
        """
        target = config.PADDLE_WIDTH * multiplier
        if abs(target - self.width) < 0.01:
            return
        center = self.center_x
        self.width = target
        self.position.x = center - target / 2.0
        self._clamp_to_playfield()

    def move(self, dt: float, direction: float, precision: bool) -> None:
        speed = config.PADDLE_SPEED
        if precision:
            speed *= config.PADDLE_PRECISION_FACTOR
        self.velocity_x = direction * speed
        self.position.x += self.velocity_x * dt
        self._clamp_to_playfield()

    def _clamp_to_playfield(self) -> None:
        field_rect = config.PLAYFIELD
        self.position.x = max(field_rect.left, self.position.x)
        self.position.x = min(field_rect.right - self.width, self.position.x)

    def draw(self, surface: pygame.Surface, show_gun: bool = False) -> None:
        rect = self.rect
        pygame.draw.rect(surface, config.COLOR_PADDLE, rect, border_radius=6)
        highlight = pygame.Rect(rect.left + 5, rect.top + 3, max(0, rect.width - 10), 3)
        pygame.draw.rect(surface, config.COLOR_PADDLE_EDGE, highlight, border_radius=2)
        if show_gun:
            barrel = pygame.Rect(rect.centerx - 3, rect.top - 10, 6, 12)
            pygame.draw.rect(surface, config.COLOR_GUN, barrel, border_radius=2)
