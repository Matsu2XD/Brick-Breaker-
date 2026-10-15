"""Tijolo: alvo destrutivel que da pontos."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from src import config


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel * factor))) for channel in color)  # type: ignore[return-value]


@dataclass
class Brick:
    column: int
    row: int
    rect: pygame.Rect
    hp: int = 1
    max_hp: int = 1
    # (inteiro, rachado) — compartilhados por todos os tijolos da mesma linha.
    sprites: tuple[pygame.Surface | None, pygame.Surface | None] = (None, None)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def score_value(self) -> int:
        return config.SCORE_PER_BRICK * self.max_hp

    @property
    def color(self) -> tuple[int, int, int]:
        return config.BRICK_ROW_COLORS[self.row % len(config.BRICK_ROW_COLORS)]

    def damage(self) -> bool:
        self.hp -= 1
        return self.hp <= 0

    def draw(self, surface: pygame.Surface) -> None:
        sprite = self.sprites[0] if self.hp >= self.max_hp else self.sprites[1]
        if sprite is not None:
            surface.blit(sprite, self.rect)
            return

        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
        if self.hp < self.max_hp:
            inner = self.rect.inflate(-10, -10)
            pygame.draw.rect(surface, _shade(self.color, 0.45), inner, border_radius=4)
