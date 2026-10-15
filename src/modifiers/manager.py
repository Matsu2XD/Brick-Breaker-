"""Pilha de modificadores ativos: duracao, acumulos e agregacao de efeitos.

Os efeitos **declaram** dados; quem consulta e o ``Game``. Nenhum modificador
muta o estado da raquete ou da bola diretamente, o que evita ter que desfazer
efeito quando ele expira.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from src import config
from src.modifiers.specs import BUFFS, DEBUFFS, Drop, ModifierSpec, Polarity


@dataclass
class ActiveEffect:
    spec: ModifierSpec
    remaining: float
    stacks: int = 1


@dataclass
class ModifierManager:
    rng: random.Random
    effects: dict[str, ActiveEffect] = field(default_factory=dict)
    score_stacks: int = 0
    gun_shots: int = 0
    bricks_destroyed: int = 0
    bricks_since_drop: int = 0

    # ----------------------------------------------------------- ciclo ----
    def update(self, dt: float) -> list[ModifierSpec]:
        expired: list[ModifierSpec] = []
        for key in list(self.effects):
            effect = self.effects[key]
            if effect.spec.duration <= 0.0:
                continue
            effect.remaining -= dt
            if effect.remaining <= 0.0:
                del self.effects[key]
                expired.append(effect.spec)
        return expired

    def on_level_start(self) -> None:
        """Fase nova: toda a pilha de efeitos e a municao saem."""
        self.effects.clear()
        self.gun_shots = 0

    def on_life_lost(self) -> None:
        """Perder uma vida limpa os buffs, mas os debuffs continuam correndo.

        Limpar os debuffs ao morrer daria ao jogador um jeito de se livrar da
        punicao de proposito: bastaria deixar a bola cair. O castigo tem que
        persistir ate o tempo acabar.
        """
        for key in list(self.effects):
            if self.effects[key].spec.polarity is Polarity.BUFF:
                del self.effects[key]
        self.gun_shots = 0

    def reset(self) -> None:
        self.effects.clear()
        self.score_stacks = 0
        self.gun_shots = 0
        self.bricks_destroyed = 0
        self.bricks_since_drop = 0

    # ---------------------------------------------------------- sorteio ---
    def roll_drop(self, at_ball_cap: bool) -> Drop | None:
        self.bricks_destroyed += 1
        self.bricks_since_drop += 1

        forced = self.bricks_since_drop >= config.CAPSULE_PITY_THRESHOLD
        if not forced and self.rng.random() >= config.CAPSULE_DROP_CHANCE:
            return None

        self.bricks_since_drop = 0
        return self._pick(at_ball_cap)

    def force_drop(self, at_ball_cap: bool = False) -> Drop:
        """Sorteia um modificador ignorando a chance de queda.

        Usado por onde a capsula e merecida, nao sorteada: a recompensa de
        sequencia e o evento Chuva de Capsulas.
        """
        self.bricks_since_drop = 0
        return self._pick(at_ball_cap)

    def _pick(self, at_ball_cap: bool) -> Drop:
        debuff_allowed = self.bricks_destroyed >= config.CAPSULE_MIN_BRICKS_BEFORE_DEBUFF
        if debuff_allowed and self.rng.random() >= config.CAPSULE_BUFF_BIAS:
            pool = DEBUFFS
        else:
            pool = BUFFS

        candidates = [spec for spec in pool if self._available(spec, at_ball_cap)] or list(pool)
        spec = self.rng.choices(candidates, weights=[item.weight for item in candidates])[0]

        magnitude = 0
        if spec.id == "ball_multiplier":
            magnitude = self.rng.choices(
                config.BALL_MULTIPLIER_FACTORS,
                weights=config.BALL_MULTIPLIER_WEIGHTS,
            )[0]
        return Drop(spec=spec, magnitude=magnitude)

    def _available(self, spec: ModifierSpec, at_ball_cap: bool) -> bool:
        if not self._available_id(spec.id, at_ball_cap):
            return False
        return spec.id not in self.effects

    def _available_id(self, identifier: str, at_ball_cap: bool) -> bool:
        if identifier == "ball_multiplier":
            return not at_ball_cap
        if identifier == "score_multiplier":
            return self.score_stacks < config.SCORE_MULTIPLIER_MAX_STACKS
        if identifier == "gun":
            return self.gun_shots < config.GUN_MAX_SHOTS
        return True

    # ------------------------------------------------------- aplicacao ---
    def activate(self, drop: Drop) -> None:
        """Aplica o que o gerenciador controla. Bola extra e do ``Game``."""
        spec = drop.spec
        if spec.id == "score_multiplier":
            self.score_stacks = min(
                config.SCORE_MULTIPLIER_MAX_STACKS, self.score_stacks + 1
            )
            return
        if spec.id == "gun":
            self.gun_shots = min(
                config.GUN_MAX_SHOTS, self.gun_shots + config.GUN_SHOTS_PER_PICKUP
            )
            return
        if spec.duration <= 0.0:
            return

        effect = self.effects.get(spec.id)
        if effect is None:
            self.effects[spec.id] = ActiveEffect(spec=spec, remaining=spec.duration)
        else:
            effect.stacks += 1
            effect.remaining = spec.duration

    def consume_shot(self) -> bool:
        if self.gun_shots <= 0:
            return False
        self.gun_shots -= 1
        return True

    # ------------------------------------------------------ consultas ----
    @property
    def score_multiplier(self) -> float:
        return min(
            config.SCORE_MULTIPLIER_MAX,
            config.SCORE_MULTIPLIER_STEP**self.score_stacks,
        )

    @property
    def paddle_width_multiplier(self) -> float:
        effect = self.effects.get("paddle_grow")
        if effect is None:
            return 1.0
        stacks = min(effect.stacks, config.PADDLE_GROW_MAX_STACKS)
        return 1.0 + (config.PADDLE_GROW_FACTOR - 1.0) * stacks

    @property
    def ball_speed_multiplier(self) -> float:
        effect = self.effects.get("fast_balls")
        if effect is None:
            return 1.0
        stacks = min(effect.stacks, config.FAST_BALLS_MAX_STACKS)
        return config.FAST_BALLS_MULTIPLIER**stacks

    @property
    def controls_inverted(self) -> bool:
        return "inverted_controls" in self.effects

    @property
    def invaders_active(self) -> bool:
        return "invaders" in self.effects

    @property
    def gun_active(self) -> bool:
        return self.gun_shots > 0

    def timed_effects(self) -> list[ActiveEffect]:
        return [effect for effect in self.effects.values() if effect.spec.duration > 0.0]
