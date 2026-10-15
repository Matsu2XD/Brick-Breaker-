"""Eventos aleatorios: regras globais que mudam por alguns segundos.

Um evento nao e um modificador. O modificador e coletado pelo jogador e altera o
estado **dele**; o evento acontece com ou sem a permissao dele e altera o
**mundo**. Os dois convivem porque resolvem problemas diferentes: o modificador
premia, o evento surpreende.

Todo evento e anunciado por um letreiro. Isso e deliberado: metade da graca de um
apagao e saber que ele esta vindo, e metade da graca de uma invasao e o susto.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field

from src import config


class Mood(enum.Enum):
    """Como o evento trata o jogador."""

    BOON = "boon"
    THREAT = "threat"
    CHAOS = "chaos"


@dataclass(frozen=True)
class EventSpec:
    id: str
    name: str
    chip: str
    mood: Mood
    weight: int
    duration: float
    summary: str


EVENTS: tuple[EventSpec, ...] = (
    EventSpec(
        "capsule_rain",
        "CHUVA DE CAPSULAS",
        "CAPSULAS",
        Mood.BOON,
        18,
        0.0,
        "Cinco capsulas caem de uma vez pela largura do campo.",
    ),
    EventSpec(
        "ball_frenzy",
        "FRENESI DE BOLAS",
        "FRENESI",
        Mood.BOON,
        16,
        0.0,
        "O campo se enche de bolas de uma vez.",
    ),
    EventSpec(
        "free_gun",
        "TIRO LIVRE",
        "TIRO LIVRE",
        Mood.BOON,
        14,
        9.0,
        "O canhao fica sem limite de municao.",
    ),
    EventSpec(
        "safety_net",
        "REDE DE SEGURANCA",
        "REDE",
        Mood.BOON,
        12,
        12.0,
        "A base do campo fecha e devolve a bola.",
    ),
    EventSpec(
        "invasion",
        "INVASAO",
        "INVASAO",
        Mood.THREAT,
        16,
        0.0,
        "Uma leva de invasores aparece de uma vez.",
    ),
    EventSpec(
        "blackout",
        "APAGAO",
        "APAGAO",
        Mood.THREAT,
        12,
        8.0,
        "O campo escurece e so a bandeja e as bolas iluminam.",
    ),
    EventSpec(
        "wild_ball",
        "BOLA LOUCA",
        "BOLA LOUCA",
        Mood.THREAT,
        12,
        8.0,
        "A bola acelera sem parar enquanto o evento durar.",
    ),
)

BY_ID: dict[str, EventSpec] = {spec.id: spec for spec in EVENTS}


def mood_color(mood: Mood) -> tuple[int, int, int]:
    if mood is Mood.BOON:
        return config.COLOR_EVENT_BOON
    if mood is Mood.THREAT:
        return config.COLOR_EVENT_THREAT
    return config.COLOR_EVENT_CHAOS


@dataclass
class RunningEvent:
    spec: EventSpec
    remaining: float
    elapsed: float = 0.0


@dataclass
class EventDirector:
    """Sorteia quando o proximo evento acontece e controla os que estao rodando."""

    rng: random.Random
    next_in: float = config.EVENT_FIRST_GAP
    running: dict[str, RunningEvent] = field(default_factory=dict)
    last_id: str = ""

    def update(self, dt: float) -> EventSpec | None:
        for key in list(self.running):
            event = self.running[key]
            event.remaining -= dt
            event.elapsed += dt
            if event.remaining <= 0.0:
                del self.running[key]

        self.next_in -= dt
        if self.next_in > 0.0:
            return None
        return self.force_next()

    def force_next(self) -> EventSpec:
        """Sorteia o proximo evento e reagenda o seguinte.

        Nao inicia o evento: quem inicia e o ``Game``, no unico lugar que sabe
        aplicar os efeitos. Separar as duas coisas e o que permite disparar um
        evento direto (ferramentas de teste) sem passar pelo relogio.
        """
        spec = self._pick()
        self.last_id = spec.id
        self.next_in = self.rng.uniform(config.EVENT_MIN_GAP, config.EVENT_MAX_GAP)
        return spec

    def start(self, spec: EventSpec) -> None:
        self.last_id = spec.id
        if spec.duration > 0.0:
            self.running[spec.id] = RunningEvent(spec=spec, remaining=spec.duration)

    def clear(self) -> None:
        self.running.clear()
        self.next_in = config.EVENT_FIRST_GAP

    def _pick(self) -> EventSpec:
        pool = [
            spec
            for spec in EVENTS
            if spec.id != self.last_id and spec.id not in self.running
        ] or [spec for spec in EVENTS if spec.id != self.last_id] or list(EVENTS)
        return self.rng.choices(pool, weights=[spec.weight for spec in pool])[0]

    def is_running(self, identifier: str) -> bool:
        return identifier in self.running

    def remaining(self, identifier: str) -> float:
        event = self.running.get(identifier)
        return event.remaining if event is not None else 0.0

    @property
    def ball_speed_multiplier(self) -> float:
        event = self.running.get("wild_ball")
        if event is None:
            return 1.0
        return min(config.WILD_BALL_MAX, 1.0 + event.elapsed * config.WILD_BALL_RAMP)

    def active_names(self) -> list[str]:
        return [event.spec.name for event in self.running.values()]
