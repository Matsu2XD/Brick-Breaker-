"""Sons do jogo: carregamento, mapeamento por evento e reproducao tolerante a falhas.

O banco e deliberadamente tolerante: se o mixer nao inicializar, se a pasta nao
existir ou se um arquivo estiver corrompido, o jogo continua rodando em silencio.
E isso que permite os testes rodarem em modo headless.

A trilha usa ``pygame.mixer.music`` (streaming do disco) em vez de ``Sound``: uma
faixa de 100 s decodificada inteira na memoria seria desperdicio, e o mixer reserva
um canal proprio para ela, entao nunca rouba um canal de efeito.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import pygame

from src import config

# Cada evento aponta para uma lista de arquivos candidatos, do mais especifico
# para o mais generico. O primeiro que existir em ``sounds/`` vence, entao basta
# largar um ``shoot_sound.wav`` na pasta para o tiro ganhar som proprio.
EVENT_SOURCES: dict[str, tuple[str, ...]] = {
    "wall": ("wall_sound", "ball_sound"),
    "paddle": ("paddle_sound", "ball_sound"),
    "brick": ("brick_sound", "ball_sound"),
    "shoot": ("shoot_sound", "ball_sound"),
    "power_up": ("power_up_sound",),
    "debuff": ("debuff_sound", "power_up_sound"),
    "lose_ball": ("lose_ball_sound",),
    "level_complete": ("level_complete_sound",),
    "game_over": ("game_over_sound", "lose_ball_sound"),
    "invader": ("invader_sound", "ball_sound"),
    "menu": ("menu_sound", "ball_sound"),
}

# O mesmo sample serve para varios eventos: o volume e o que diferencia.
EVENT_VOLUME: dict[str, float] = {
    "wall": 0.35,
    "paddle": 0.80,
    "brick": 0.50,
    "shoot": 0.40,
    "power_up": 0.90,
    "debuff": 0.90,
    "lose_ball": 0.95,
    "level_complete": 0.95,
    "game_over": 0.95,
    "invader": 0.55,
    "menu": 0.60,
}

# Impede que rajadas de eventos empilhem o mesmo sample no mesmo frame.
EVENT_COOLDOWN: dict[str, float] = {
    "wall": 0.03,
    "paddle": 0.05,
    "brick": 0.03,
    "shoot": 0.06,
    "power_up": 0.30,
    "debuff": 0.30,
    "lose_ball": 0.50,
    "level_complete": 0.50,
    "game_over": 0.50,
    "invader": 0.05,
    "menu": 0.10,
}

# Um canal dedicado por evento: repetir um som interrompe a si mesmo, nunca os outros.
EVENT_CHANNEL: dict[str, int] = {
    "wall": 0,
    "brick": 1,
    "paddle": 2,
    "shoot": 3,
    "invader": 4,
    "power_up": 5,
    "debuff": 6,
    "lose_ball": 7,
    "level_complete": 8,
    "game_over": 9,
    "menu": 10,
}

MIXER_CHANNELS = 16


def is_music(stem: str) -> bool:
    """Um arquivo e trilha quando o nome comeca com um dos prefixos conhecidos."""
    lowered = stem.lower()
    return any(lowered.startswith(prefix) for prefix in config.MUSIC_PREFIXES)


@dataclass
class SoundBank:
    """Biblioteca de efeitos e a trilha, indexadas por evento de jogo."""

    volume: float = config.SOUND_VOLUME
    enabled: bool = True
    muted: bool = False
    available: bool = False
    music_path: str | None = None
    music_on: bool = True
    music_level: float = config.MUSIC_VOLUME
    library: dict[str, pygame.mixer.Sound] = field(default_factory=dict)
    sounds: dict[str, pygame.mixer.Sound] = field(default_factory=dict)
    channels: dict[str, pygame.mixer.Channel] = field(default_factory=dict)
    last_played: dict[str, float] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    _music_loaded: bool = False

    def __post_init__(self) -> None:
        self.available = self._start_mixer()
        if not self.available:
            return
        self._load_library()
        self._bind_events()

    # ------------------------------------------------------------ setup ----
    def _start_mixer(self) -> bool:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.pre_init(config.SOUND_SAMPLE_RATE, -16, 2, 512)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(MIXER_CHANNELS)
        except (pygame.error, AttributeError):
            return False
        return True

    def _load_library(self) -> None:
        if not os.path.isdir(config.SOUND_DIR):
            return
        for name in sorted(os.listdir(config.SOUND_DIR)):
            if not name.lower().endswith((".wav", ".ogg", ".mp3", ".flac")):
                continue
            stem = os.path.splitext(name)[0]
            path = os.path.join(config.SOUND_DIR, name)
            if is_music(stem):
                if self.music_path is None:
                    self.music_path = path
                continue
            try:
                self.library[stem] = pygame.mixer.Sound(path)
            except pygame.error:
                continue

    def _bind_events(self) -> None:
        for event, candidates in EVENT_SOURCES.items():
            for candidate in candidates:
                sound = self.library.get(candidate)
                if sound is None:
                    continue
                self.sounds[event] = sound
                break
            else:
                self.missing.append(event)

        for event, index in EVENT_CHANNEL.items():
            if index < MIXER_CHANNELS and event in self.sounds:
                self.channels[event] = pygame.mixer.Channel(index)

        self.apply_volumes()

    def apply_volumes(self) -> None:
        """Distribui o volume em dois niveis, e nao em um so.

        O **master** vai no ``Sound``; o **balanco de cada evento** vai no canal.
        A separacao nao e capricho: varios eventos caem no mesmo arquivo (parede,
        tijolo, bandeja, tiro e invasor usam o ``ball_sound``), e ``set_volume``
        de um ``Sound`` e propriedade do objeto — o ultimo a escrever venceria
        para todos. Cada evento tem canal proprio, entao o canal e o lugar certo
        para diferenciar. O mixer multiplica os dois, entao o resultado final e
        master x balanco, exatamente o que se quer.
        """
        seen: set[int] = set()
        for sound in self.sounds.values():
            if id(sound) in seen:
                continue
            seen.add(id(sound))
            sound.set_volume(self.volume)
        for event, channel in self.channels.items():
            channel.set_volume(EVENT_VOLUME.get(event, 1.0))

    # ------------------------------------------------------------- music ---
    @property
    def music_available(self) -> bool:
        return self.available and self.music_path is not None

    def start_music(self) -> bool:
        if not (self.music_available and self.music_on):
            return False
        try:
            # Idempotente de proposito: os ajustes chamam isto a cada mudanca, e
            # reiniciar a faixa do zero toda vez soaria como um disco pulando.
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume(self.music_level)
                return True
            if not self._music_loaded:
                pygame.mixer.music.load(self.music_path)
                self._music_loaded = True
            pygame.mixer.music.set_volume(self.music_level)
            pygame.mixer.music.play(loops=-1)
        except pygame.error:
            self.music_path = None
            self._music_loaded = False
            return False
        return True

    def stop_music(self) -> None:
        if not self.available:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    def set_music_level(self, value: float) -> None:
        self.music_level = max(0.0, min(1.0, value))
        if self.available and self._music_loaded:
            try:
                pygame.mixer.music.set_volume(self.music_level)
            except pygame.error:
                pass

    def set_music_enabled(self, enabled: bool) -> None:
        self.music_on = enabled
        if enabled:
            self.start_music()
        else:
            self.stop_music()

    def set_sfx_level(self, value: float) -> None:
        self.volume = max(0.0, min(1.0, value))
        if self.available:
            self.apply_volumes()

    def set_sfx_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.stop_all()

    # ------------------------------------------------------------- play ----
    def play(self, event: str) -> bool:
        if not (self.available and self.enabled and not self.muted):
            return False
        sound = self.sounds.get(event)
        if sound is None:
            return False

        now = pygame.time.get_ticks() / 1000.0
        if now - self.last_played.get(event, -1e9) < EVENT_COOLDOWN.get(event, 0.0):
            return False
        self.last_played[event] = now

        channel = self.channels.get(event)
        if channel is not None:
            channel.play(sound)
        else:
            sound.play()
        return True

    def stop_all(self) -> None:
        if self.available:
            pygame.mixer.stop()

    def toggle_mute(self) -> bool:
        """Silencia tudo, trilha inclusive, sem mexer nos ajustes salvos."""
        self.muted = not self.muted
        if self.muted:
            self.stop_all()
            if self.available and self._music_loaded:
                try:
                    pygame.mixer.music.pause()
                except pygame.error:
                    pass
        elif self.available and self._music_loaded and self.music_on:
            try:
                pygame.mixer.music.unpause()
            except pygame.error:
                pass
        return self.muted

    def loaded_events(self) -> list[str]:
        return sorted(self.sounds)
