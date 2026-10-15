"""Catalogo de modificadores.

Este e o arquivo de *conteudo*: o que cada capsula faz, quanto dura e qual a
chance de cair. Os numeros de motor (velocidades, tamanhos, taxas de sorteio)
ficam em ``config.py``; aqui ficam os numeros de design.

Cada modificador carrega dois nomes de proposito. ``short`` e o que cabe na
capsula, que cai rapido no meio de um rebate — curto, mas em portugues e dizendo
o efeito. ``hud`` e o que aparece no chip, onde ha espaco e tempo de leitura.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Polarity(enum.Enum):
    BUFF = "buff"
    DEBUFF = "debuff"


@dataclass(frozen=True)
class ModifierSpec:
    id: str
    name: str
    short: str
    hud: str
    polarity: Polarity
    weight: int
    duration: float
    summary: str


BUFFS: tuple[ModifierSpec, ...] = (
    ModifierSpec(
        id="ball_multiplier",
        name="Multiplicador de Bolas",
        short="2 BOLAS",
        hud="BOLAS",
        polarity=Polarity.BUFF,
        weight=22,
        duration=0.0,
        summary="Multiplica as bolas em jogo (2x, 4x, 6x ou 8x), ate 8 bolas.",
    ),
    ModifierSpec(
        id="score_multiplier",
        name="Multiplicador de Pontos",
        short="PONTOS x2",
        hud="PONTOS",
        polarity=Polarity.BUFF,
        weight=20,
        duration=0.0,
        summary="Dobra a pontuacao. Acumula ate 8x.",
    ),
    ModifierSpec(
        id="paddle_grow",
        name="Bandeja Grande",
        short="BANDEJA",
        hud="BANDEJA",
        polarity=Polarity.BUFF,
        weight=20,
        duration=20.0,
        summary="Aumenta a bandeja em 25%. Acumula ate 3 vezes.",
    ),
    ModifierSpec(
        id="gun",
        name="Armamento",
        short="CANHAO",
        hud="CANHAO",
        polarity=Polarity.BUFF,
        weight=18,
        duration=0.0,
        summary="Instala um canhao na bandeja com 8 disparos. Acumula municao.",
    ),
)

DEBUFFS: tuple[ModifierSpec, ...] = (
    ModifierSpec(
        id="inverted_controls",
        name="Inversao dos Comandos",
        short="INVERTE",
        hud="INVERTIDO",
        polarity=Polarity.DEBUFF,
        weight=34,
        duration=8.0,
        summary="Inverte esquerda e direita.",
    ),
    ModifierSpec(
        id="fast_balls",
        name="Bolas Super Rapidas",
        short="RAPIDAS",
        hud="BOLAS RAPIDAS",
        polarity=Polarity.DEBUFF,
        weight=33,
        duration=8.0,
        summary="Acelera as bolas em 85%.",
    ),
    ModifierSpec(
        id="invaders",
        name="Invasores",
        short="INVASORES",
        hud="INVASORES",
        polarity=Polarity.DEBUFF,
        weight=33,
        duration=12.0,
        summary="Inimigos descem tentando acertar a bandeja.",
    ),
)

MODIFIERS: tuple[ModifierSpec, ...] = BUFFS + DEBUFFS
BY_ID: dict[str, ModifierSpec] = {spec.id: spec for spec in MODIFIERS}

# Modificadores instantaneos: nao entram na pilha de efeitos com duracao.
INSTANT_IDS = frozenset({"ball_multiplier", "score_multiplier", "gun"})


@dataclass(frozen=True)
class Drop:
    """Um sorteio concreto: qual modificador e com que magnitude."""

    spec: ModifierSpec
    magnitude: int = 0

    @property
    def label(self) -> str:
        """O texto que aparece na capsula."""
        if self.spec.id == "ball_multiplier":
            return f"{self.magnitude} BOLAS"
        return self.spec.short

    @property
    def is_buff(self) -> bool:
        return self.spec.polarity is Polarity.BUFF
