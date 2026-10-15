"""Particulas de impacto.

Sao puramente cosmeticas: nada no jogo le o estado delas. Existem porque um
tijolo que desaparece sem deixar rastro nao parece ter quebrado.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from src import config


@dataclass
class Particle:
    position: pygame.Vector2
    velocity: pygame.Vector2
    color: tuple[int, int, int]
    life: float
    span: float
    size: float

    @property
    def fade(self) -> float:
        """1.0 na hora do impacto, 0.0 ao morrer."""
        if self.span <= 0.0:
            return 0.0
        return max(0.0, self.life / self.span)


@dataclass
class ParticleSystem:
    rng: random.Random = field(default_factory=lambda: random.Random(0))
    particles: list[Particle] = field(default_factory=list)

    def burst(
        self,
        position: tuple[float, float] | pygame.Vector2,
        color: tuple[int, int, int],
        count: int,
        speed: float,
        life: float,
        direction: tuple[float, float] | None = None,
        spread_deg: float = 62.0,
    ) -> None:
        """Solta ``count`` particulas. Sem direcao o disparo e em leque total."""
        room = config.PARTICLE_MAX - len(self.particles)
        if room <= 0:
            return

        for _ in range(min(count, room)):
            if direction is None:
                angle = self.rng.uniform(0.0, math.tau)
            else:
                base = math.atan2(direction[1], direction[0])
                angle = base + math.radians(self.rng.uniform(-spread_deg, spread_deg))

            span = life * self.rng.uniform(0.65, 1.0)
            self.particles.append(
                Particle(
                    position=pygame.Vector2(position),
                    velocity=pygame.Vector2(math.cos(angle), math.sin(angle))
                    * (speed * self.rng.uniform(0.4, 1.0)),
                    color=color,
                    life=span,
                    span=span,
                    size=config.PARTICLE_SIZE * self.rng.uniform(0.7, 1.4),
                )
            )

    def update(self, dt: float) -> None:
        for particle in self.particles:
            particle.life -= dt
            particle.velocity.y += config.PARTICLE_GRAVITY * dt
            particle.position += particle.velocity * dt
        self.particles = [particle for particle in self.particles if particle.life > 0.0]

    def draw(self, surface: pygame.Surface) -> None:
        for particle in self.particles:
            size = max(1, int(particle.size * particle.fade + 0.5))
            surface.fill(
                particle.color,
                (
                    int(particle.position.x),
                    int(particle.position.y),
                    size,
                    size,
                ),
            )

    def clear(self) -> None:
        self.particles.clear()

    def __len__(self) -> int:
        return len(self.particles)
