"""Infraestrutura minima compartilhada pelos testes.

Deixa o ambiente headless (sem janela nem placa de som) e expoe o helper de
checagem. Rodar os testes nao depende de pytest nem de display.
"""

from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Os testes mexem em ajustes e placar. Sem isto, simular um fim de jogo gravaria
# a pontuacao do teste no placar de quem esta jogando.
from src import config  # noqa: E402

config.SAVE_DIR = tempfile.mkdtemp(prefix="brickbreaker-test-")
atexit.register(shutil.rmtree, config.SAVE_DIR, ignore_errors=True)

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if not condition:
        failures.append(label)
    print(f"[{'ok  ' if condition else 'FAIL'}] {label} {detail}")


def finish(title: str) -> int:
    print()
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        return 1
    print(f"{title}: all checks passed")
    return 0
