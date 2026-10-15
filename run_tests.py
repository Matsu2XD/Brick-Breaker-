"""Roda toda a suite de testes: python run_tests.py

Sem pytest, sem display e sem placa de som. Cada suite roda em um processo
proprio para que um vazamento de uma nao contamine a seguinte.
"""

from __future__ import annotations

import os
import subprocess
import sys

SUITES = (
    ("Física e controles", "tests/test_physics.py"),
    ("Renderização e layout", "tests/test_layout.py"),
    ("Power-ups, debuffs e áudio", "tests/test_powerups.py"),
    ("Dinâmica: partículas, sequência e eventos", "tests/test_dynamics.py"),
    ("Interface, ajustes, placar e trilha", "tests/test_ui.py"),
    ("Documento de design", "tests/test_design_doc.py"),
)

ROOT = os.path.dirname(os.path.abspath(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    environment = dict(os.environ)
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    environment["PYTHONIOENCODING"] = "utf-8"

    failed: list[str] = []
    for title, path in SUITES:
        print(f"--- {title} " + "-" * max(0, 60 - len(title)))
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, path)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        checks = result.stdout.count("[ok  ]")
        problems = result.stdout.count("[FAIL]")
        for line in result.stdout.splitlines():
            if line.startswith("[FAIL]"):
                print(line)
        status = "ok" if result.returncode == 0 else "FALHOU"
        print(f"    {checks} verificações, {problems} falhas -> {status}")
        if result.returncode != 0:
            failed.append(title)
            if result.stderr.strip():
                print(result.stderr.strip()[-2000:])
        print()

    if failed:
        print(f"SUITES COM FALHA: {failed}")
        return 1
    print("Todas as suítes passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
