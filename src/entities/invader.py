"""Invasor: inimigo do debuff Invasores, desce tentando acertar a bandeja."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from src import config


@dataclass
class Invader:
    position: pygame.Vector2
    velocity: pygame.Vector2
    width: int = config.INVADER_WIDTH
    height: int = config.INVADER_HEIGHT
    alive: bool = True
    wobble: float = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.position.x - self.width / 2),
            int(self.position.y - self.height / 2),
            self.width,
            self.height,
        )

    def update(self, dt: float, playfield: pygame.Rect) -> None:
        self.position += self.velocity * dt
        self.wobble += dt * 7.0
        half = self.width / 2.0
        if self.position.x - half < playfield.left:
            self.position.x = playfield.left + half
            self.velocity.x = abs(self.velocity.x)
        elif self.position.x + half > playfield.right:
            self.position.x = playfield.right - half
            self.velocity.x = -abs(self.velocity.x)

    def is_off(self, playfield: pygame.Rect) -> bool:
        return self.position.y - self.height / 2 > playfield.bottom

    def draw(self, surface: pygame.Surface) -> None:
        rect = self.rect
        pygame.draw.rect(surface, config.COLOR_INVADER, rect, border_radius=6)

        eye_y = rect.top + rect.height // 3
        sway = int(math.sin(self.wobble) * 2)
        for offset in (-rect.width // 4, rect.width // 4):
            pygame.draw.circle(
                surface,
                config.COLOR_INVADER_EYE,
                (rect.centerx + offset + sway, eye_y),
                3,
            )

        leg_y = rect.bottom - 2
        for offset in (-rect.width // 3, 0, rect.width // 3):
            pygame.draw.line(
                surface,
                config.COLOR_INVADER,
                (rect.centerx + offset, leg_y),
                (rect.centerx + offset, leg_y + 5),
                2,
            )
