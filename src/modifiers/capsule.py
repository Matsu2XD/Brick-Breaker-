"""Capsula que cai de um tijolo destruido e e capturada pela bandeja."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from src import config
from src.modifiers.specs import Drop


@dataclass
class Capsule:
    drop: Drop
    position: pygame.Vector2
    velocity: pygame.Vector2
    width: int = config.CAPSULE_WIDTH
    height: int = config.CAPSULE_HEIGHT
    collected: bool = False

    @classmethod
    def falling_from(cls, drop: Drop, origin: tuple[int, int]) -> "Capsule":
        return cls(
            drop=drop,
            position=pygame.Vector2(float(origin[0]), float(origin[1])),
            velocity=pygame.Vector2(0.0, config.CAPSULE_SPEED),
        )

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.position.x - self.width / 2),
            int(self.position.y - self.height / 2),
            self.width,
            self.height,
        )

    @property
    def color(self) -> tuple[int, int, int]:
        if self.drop.is_buff:
            return config.COLOR_CAPSULE_BUFF
        return config.COLOR_CAPSULE_DEBUFF

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt

    def is_lost(self) -> bool:
        return self.position.y - self.height / 2 > config.PLAYFIELD.bottom

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Pilula escura com faixa e texto na cor da polaridade.

        O nome **por extenso** e o unico jeito de o jogador saber o que vai pegar:
        os icones do pack sao todos o mesmo quadrado em cores diferentes, entao
        nao dizem nada sobre o efeito.
        """
        rect = self.rect
        color = self.color

        pygame.draw.rect(surface, config.COLOR_CAPSULE_INNER, rect, border_radius=7)
        pygame.draw.rect(surface, color, rect, width=2, border_radius=7)

        strip = pygame.Rect(rect.left + 4, rect.top + 5, 4, rect.height - 10)
        pygame.draw.rect(surface, color, strip, border_radius=2)

        label = font.render(self.drop.label, True, color)
        surface.blit(label, label.get_rect(center=(rect.centerx + 5, rect.centery)))
