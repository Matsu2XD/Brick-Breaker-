"""Construcao do layout de tijolos."""

from __future__ import annotations

import pygame

from src import config
from src.entities.brick import Brick


def build_bricks(playfield: pygame.Rect, sheet=None) -> list[Brick]:
    """Monta a grade de tijolos encaixada na largura util do campo.

    Os sprites sao buscados **uma vez por linha**, nao por tijolo: os 11 tijolos
    de uma linha compartilham as mesmas duas superficies ja escaladas.
    """
    columns = config.BRICK_COLUMNS
    rows = config.BRICK_ROWS
    gap = config.BRICK_GAP
    cell_width = (playfield.width - gap * (columns + 1)) / columns
    brick_width = int(cell_width)

    bricks: list[Brick] = []
    for row in range(rows):
        sprites: tuple[pygame.Surface | None, ...] = (None, None)
        if sheet is not None and sheet.available:
            sprites = sheet.brick_pair(row, (brick_width, config.BRICK_HEIGHT))

        hp = 2 if row < config.BRICK_TOUGH_ROWS else 1
        top = int(
            playfield.top
            + config.BRICK_TOP_OFFSET
            + row * (config.BRICK_HEIGHT + gap)
        )
        for column in range(columns):
            left = int(playfield.left + gap + column * (cell_width + gap))
            bricks.append(
                Brick(
                    column=column,
                    row=row,
                    rect=pygame.Rect(left, top, brick_width, config.BRICK_HEIGHT),
                    hp=hp,
                    max_hp=hp,
                    sprites=sprites,
                )
            )
    return bricks
