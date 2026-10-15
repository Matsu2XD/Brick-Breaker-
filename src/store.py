"""Persistencia em JSON: ajustes e placar de lideres.

Tudo aqui falha para o padrao **em silencio**. Um jogo que se recusa a abrir
porque o arquivo de placar corrompeu e pior que um jogo sem placar, e o jogador
nao tem como consertar um arquivo que ele nunca viu.

A escrita e atomica (arquivo temporario + ``os.replace``) para que um desligamento
no meio do salvamento nao deixe um JSON pela metade.
"""

from __future__ import annotations

import json
import os

from src import config


def _path(name: str) -> str:
    return os.path.join(config.SAVE_DIR, name)


def load(name: str, default: dict) -> dict:
    """Le um JSON do diretorio de save, preenchendo o que faltar com ``default``."""
    try:
        with open(_path(name), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return dict(default)
    if not isinstance(data, dict):
        return dict(default)
    return {**default, **data}


def save(name: str, data: dict) -> bool:
    """Grava um JSON. Devolve False quando nao deu, sem levantar."""
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        temporary = _path(name) + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        os.replace(temporary, _path(name))
        return True
    except (OSError, TypeError, ValueError):
        return False
