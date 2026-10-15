"""Menus: tela inicial, pausa, ajustes e placar.

Este modulo **nao importa pygame**: ele decide apenas *o que* esta na tela e *o
que cada tecla faz*. Quem desenha e o ``game.py``. A separacao existe para que a
navegacao — trocar de tela, mexer num valor, voltar — possa ser testada sem
abrir janela, e para que a logica do menu nao se misture com o desenho.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from src.settings import Settings


class Screen(enum.Enum):
    MAIN = "main"
    PAUSED = "paused"
    SETTINGS = "settings"
    SCORES = "scores"


class Kind(enum.Enum):
    ACTION = "action"
    TOGGLE = "toggle"
    SLIDER = "slider"


@dataclass(frozen=True)
class MenuItem:
    label: str
    kind: Kind = Kind.ACTION
    action: str = ""
    setting: str = ""


MAIN_ITEMS: tuple[MenuItem, ...] = (
    MenuItem("JOGAR", action="play"),
    MenuItem("PLACAR", action="scores"),
    MenuItem("AJUSTES", action="settings"),
    MenuItem("SAIR", action="quit"),
)

PAUSED_ITEMS: tuple[MenuItem, ...] = (
    MenuItem("CONTINUAR", action="resume"),
    MenuItem("AJUSTES", action="settings"),
    MenuItem("RECOMECAR", action="restart"),
    MenuItem("ABANDONAR", action="main"),
)

SETTINGS_ITEMS: tuple[MenuItem, ...] = (
    MenuItem("Musica", Kind.TOGGLE, setting="music_enabled"),
    MenuItem("Volume da musica", Kind.SLIDER, setting="music_volume"),
    MenuItem("Efeitos", Kind.TOGGLE, setting="sfx_enabled"),
    MenuItem("Volume dos efeitos", Kind.SLIDER, setting="sfx_volume"),
    MenuItem("Particulas", Kind.TOGGLE, setting="particles"),
    MenuItem("Tremor de tela", Kind.TOGGLE, setting="screen_shake"),
    MenuItem("Teclas de teste", Kind.TOGGLE, setting="debug_keys"),
    MenuItem("Voltar", action="back"),
)

ITEMS: dict[Screen, tuple[MenuItem, ...]] = {
    Screen.MAIN: MAIN_ITEMS,
    Screen.PAUSED: PAUSED_ITEMS,
    Screen.SETTINGS: SETTINGS_ITEMS,
    Screen.SCORES: (),
}

SLIDER_STEP = 0.1


@dataclass
class Menu:
    """Navegacao dos menus. Guarda so o estado; nao desenha nada."""

    settings: Settings
    screen: Screen = Screen.MAIN
    cursor: int = 0
    return_to: Screen = Screen.MAIN

    @property
    def items(self) -> tuple[MenuItem, ...]:
        return ITEMS[self.screen]

    @property
    def current(self) -> MenuItem | None:
        items = self.items
        if not items:
            return None
        return items[min(self.cursor, len(items) - 1)]

    def move(self, delta: int) -> None:
        items = self.items
        if not items:
            return
        self.cursor = (self.cursor + delta) % len(items)

    def open(self, screen: Screen) -> None:
        """Troca de tela lembrando de onde veio, para o "Voltar" funcionar."""
        if screen is not self.screen:
            self.return_to = self.screen
        self.screen = screen
        self.cursor = 0

    def back(self) -> Screen:
        self.screen = self.return_to
        self.cursor = 0
        return self.screen

    def adjust(self, direction: int) -> None:
        """Mexe no item atual: inverte um interruptor ou anda um degrau no volume."""
        item = self.current
        if item is None:
            return
        if item.kind is Kind.TOGGLE:
            setattr(self.settings, item.setting,
                    not getattr(self.settings, item.setting))
        elif item.kind is Kind.SLIDER:
            value = getattr(self.settings, item.setting) + direction * SLIDER_STEP
            setattr(self.settings, item.setting, round(max(0.0, min(1.0, value)), 2))

    def activate(self) -> str:
        """Devolve a acao do item atual, ou "" quando nao ha o que fazer.

        Nao executa nada alem de mexer num interruptor: trocar de tela e
        responsabilidade de quem chamou, porque so o jogo sabe quais efeitos
        colaterais acompanham a troca (gravar ajustes, por exemplo).
        """
        item = self.current
        if item is None:
            return ""
        if item.kind is Kind.TOGGLE:
            self.adjust(1)
            return ""
        if item.kind is Kind.SLIDER:
            return ""
        return item.action

    def value_text(self, item: MenuItem) -> str:
        """O que aparece a direita do rotulo."""
        if item.kind is Kind.ACTION:
            return ""
        value = getattr(self.settings, item.setting)
        if item.kind is Kind.TOGGLE:
            return "LIGADO" if value else "DESLIGADO"
        return f"{int(round(value * 100))}%"
