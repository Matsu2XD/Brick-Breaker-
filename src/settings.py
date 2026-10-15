"""Ajustes do jogador, persistidos entre sessoes.

Cada campo e validado na leitura: um arquivo editado a mao ou de uma versao
antiga nao pode derrubar o jogo. Tipo errado devolve o padrao daquele campo, e
nao o arquivo inteiro.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from src import config, store


def _number(value, fallback: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return max(0.0, min(1.0, float(value)))


def _flag(value, fallback: bool) -> bool:
    return value if isinstance(value, bool) else fallback


@dataclass
class Settings:
    music_enabled: bool = True
    music_volume: float = config.MUSIC_VOLUME
    sfx_enabled: bool = True
    sfx_volume: float = config.SOUND_VOLUME
    particles: bool = True
    screen_shake: bool = True
    debug_keys: bool = config.DEBUG_KEYS_ENABLED

    @classmethod
    def load(cls) -> "Settings":
        defaults = cls()
        raw = store.load(config.SETTINGS_FILE, asdict(defaults))
        return cls(
            music_enabled=_flag(raw.get("music_enabled"), defaults.music_enabled),
            music_volume=_number(raw.get("music_volume"), defaults.music_volume),
            sfx_enabled=_flag(raw.get("sfx_enabled"), defaults.sfx_enabled),
            sfx_volume=_number(raw.get("sfx_volume"), defaults.sfx_volume),
            particles=_flag(raw.get("particles"), defaults.particles),
            screen_shake=_flag(raw.get("screen_shake"), defaults.screen_shake),
            debug_keys=_flag(raw.get("debug_keys"), defaults.debug_keys),
        )

    def save(self) -> bool:
        return store.save(config.SETTINGS_FILE, asdict(self))

    def reset(self) -> None:
        """Volta tudo ao padrao, mantendo o objeto (o menu guarda a referencia)."""
        for field in fields(self):
            setattr(self, field.name, getattr(Settings(), field.name))
