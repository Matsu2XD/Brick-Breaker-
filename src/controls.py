"""Traducao do teclado para um estado de entrada imutavel.

Mapeamento (WASD e setas fazem o mesmo):

    A / seta esquerda ....... mover a bandeja para a esquerda
    D / seta direita ........ mover a bandeja para a direita
    S / seta baixo .......... modo precisao (movimento fino, util para mirar)
    W / seta cima / espaco .. lancar a bola (toque) e atirar (segurando)
    P ....................... pausar / retomar
    R ....................... reiniciar a partida
    M ....................... ligar / desligar o som
    ESC ..................... sair

Teclas de teste (ver config.DEBUG_KEYS_ENABLED):

    1 a 7 ................... solta na tela o modificador correspondente
    0 ....................... limpa todos os modificadores ativos
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

LEFT_KEYS = (pygame.K_a, pygame.K_LEFT)
RIGHT_KEYS = (pygame.K_d, pygame.K_RIGHT)
PRECISION_KEYS = (pygame.K_s, pygame.K_DOWN)
LAUNCH_KEYS = (pygame.K_w, pygame.K_UP, pygame.K_SPACE)

HINT_LINE = "A/D mover  |  S precisao  |  W lancar/atirar  |  M som  |  P pausa"


@dataclass(frozen=True)
class InputState:
    """Leitura do teclado valida para um frame inteiro."""

    move: float = 0.0
    precision: bool = False
    action: bool = False

    @classmethod
    def from_keyboard(cls) -> "InputState":
        keys = pygame.key.get_pressed()
        move = 0.0
        if any(keys[key] for key in LEFT_KEYS):
            move -= 1.0
        if any(keys[key] for key in RIGHT_KEYS):
            move += 1.0
        return cls(
            move=move,
            precision=any(keys[key] for key in PRECISION_KEYS),
            action=any(keys[key] for key in LAUNCH_KEYS),
        )
