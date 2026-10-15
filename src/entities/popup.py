"""Placar flutuante: o "+800" que sobe do tijolo destruido.

Existe por clareza, nao por enfeite. O jogo tem multiplicador de pontos, bonus
de sequencia e eventos que mexem no placar, e sem ver o numero subir o jogador
nao tem como perceber que essas coisas estao funcionando.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from src import config


@dataclass
class Popup:
    text: str
    position: pygame.Vector2
    color: tuple[int, int, int]
    life: float
    span: float

    @property
    def fade(self) -> float:
        if self.span <= 0.0:
            return 0.0
        return max(0.0, self.life / self.span)


@dataclass
class PopupSystem:
    popups: list[Popup] = field(default_factory=list)

    def spawn(self, text: str, position: tuple[float, float],
              color: tuple[int, int, int]) -> None:
        if len(self.popups) >= config.POPUP_MAX:
            self.popups.pop(0)
        self.popups.append(
            Popup(
                text=text,
                position=pygame.Vector2(position),
                color=color,
                life=config.POPUP_LIFE,
                span=config.POPUP_LIFE,
            )
        )

    def update(self, dt: float) -> None:
        for popup in self.popups:
            popup.life -= dt
            popup.position.y -= config.POPUP_RISE * dt
        self.popups = [popup for popup in self.popups if popup.life > 0.0]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        for popup in self.popups:
            text = font.render(popup.text, True, popup.color)
            text.set_alpha(int(255 * min(1.0, popup.fade * 2.0)))
            x = int(popup.position.x) - text.get_width() // 2
            y = int(popup.position.y) - text.get_height() // 2
            shadow = font.render(popup.text, True, (8, 10, 20))
            shadow.set_alpha(int(190 * min(1.0, popup.fade * 2.0)))
            surface.blit(shadow, (x + 2, y + 2))
            surface.blit(text, (x, y))

    def clear(self) -> None:
        self.popups.clear()

    def __len__(self) -> int:
        return len(self.popups)
