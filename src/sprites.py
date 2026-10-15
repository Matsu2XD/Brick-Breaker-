"""Carregamento do pacote de sprites.

O jogo inteiro funciona **sem nenhum arquivo de imagem**: toda entidade cai de
volta no desenho por primitiva quando o sprite nao existe. Isso mantem os
testes headless rodando sem assets, deixa a integracao reversivel e faz uma
falha de leitura virar "menos bonito" em vez de "quebrado".

O pack e um atlas do TexturePacker: uma folha unica mais um XML com o retangulo
de cada sprite. Os sprites sao numerados de 01 a 61 e o que cada faixa contem
esta documentado em GAME_DESIGN.md.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import pygame

from src import config


@dataclass
class SpriteSheet:
    """Recorta o atlas e entrega superficies ja no tamanho pedido."""

    available: bool = False
    sheet: pygame.Surface | None = None
    frames: dict[int, pygame.Rect] = field(default_factory=dict)
    cache: dict[tuple[int, int, int], pygame.Surface] = field(default_factory=dict)

    def load(self) -> None:
        if not (os.path.isfile(config.SPRITE_SHEET) and os.path.isfile(config.SPRITE_ATLAS)):
            return
        try:
            self.sheet = pygame.image.load(config.SPRITE_SHEET).convert_alpha()
            self.frames = self._parse_atlas(config.SPRITE_ATLAS)
        except (pygame.error, ET.ParseError, OSError, ValueError):
            self.sheet = None
            self.frames = {}
            return
        self.available = bool(self.frames)

    @staticmethod
    def _parse_atlas(path: str) -> dict[int, pygame.Rect]:
        frames: dict[int, pygame.Rect] = {}
        for node in ET.parse(path).getroot().iter("SubTexture"):
            name = node.get("name") or ""
            digits = "".join(character for character in name if character.isdigit())
            if not digits:
                continue
            try:
                frames[int(digits)] = pygame.Rect(
                    int(node.get("x")), int(node.get("y")),
                    int(node.get("width")), int(node.get("height")),
                )
            except (TypeError, ValueError):
                continue
        return frames

    def get(self, index: int, size: tuple[int, int]) -> pygame.Surface | None:
        """Devolve o sprite ``index`` escalado para ``size`` (com cache)."""
        if not self.available or self.sheet is None:
            return None
        rect = self.frames.get(index)
        if rect is None:
            return None

        width, height = max(1, int(size[0])), max(1, int(size[1]))
        key = (index, width, height)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        piece = self.sheet.subsurface(rect)
        scaled = (
            piece.copy()
            if piece.get_size() == (width, height)
            else pygame.transform.smoothscale(piece, (width, height))
        )
        self.cache[key] = scaled
        return scaled

    def brick_pair(self, row: int, size: tuple[int, int]) -> tuple[pygame.Surface, ...]:
        """Os dois estados do tijolo daquela linha: inteiro e rachado."""
        index = config.BRICK_ROW_SPRITES[row % len(config.BRICK_ROW_SPRITES)]
        intact = self.get(index, size)
        damaged = self.get(index + 1, size)
        return (intact, damaged)

    def ball(self, diameter: int) -> pygame.Surface | None:
        return self.get(config.SPRITE_BALL, (diameter, diameter))

    def heart(self) -> pygame.Surface | None:
        size = config.SPRITE_HEART_SIZE
        return self.get(config.SPRITE_HEART, (size, size))

    def star(self) -> pygame.Surface | None:
        size = config.SPRITE_STAR_SIZE
        return self.get(config.SPRITE_STAR, (size, size))
