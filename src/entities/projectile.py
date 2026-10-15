"""Projetil disparado pelo modificador Armamento."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from src import config


@dataclass
class Projectile:
    position: pygame.Vector2
    velocity: pygame.Vector2
    width: int = config.PROJECTILE_WIDTH
    height: int = config.PROJECTILE_HEIGHT
    alive: bool = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.position.x - self.width / 2),
            int(self.position.y - self.height / 2),
            self.width,
            self.height,
        )

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt

    def is_off(self, playfield: pygame.Rect) -> bool:
        return self.position.y + self.height / 2 < playfield.top

    def draw(self, surface: pygame.Surface) -> None:
        rect = self.rect
        pygame.draw.rect(surface, config.COLOR_PROJECTILE, rect, border_radius=2)
        pygame.draw.rect(
            surface,
            config.COLOR_PROJECTILE_CORE,
            rect.inflate(-2, -5),
            border_radius=1,
        )
