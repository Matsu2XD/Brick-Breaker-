"""Empacota o jogo num executavel unico e confere o resultado.

    python build.py

Gera ``dist/QuebrandoTijolos.exe`` (Windows) ou ``dist/QuebrandoTijolos``
(Linux) e roda o autoteste **dentro do binario**, que e a unica forma de saber
que o pacote carrega sprites, sons e trilha.

O PyInstaller **nao cross-compila**: o binario e sempre da plataforma em que o
script roda. Para os dois, rode em cada sistema (ou use a CI em
``.github/workflows/build.yml``).

Precisa de:  pip install -r requirements.txt pyinstaller
"""

from __future__ import annotations

import os
import subprocess
import sys

from src import config

ROOT = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(ROOT, "quebrando_tijolos.spec")
DIST = os.path.join(ROOT, "dist")
WORK = os.path.join(ROOT, "build")


def binary_path() -> str:
    name = config.APP_NAME + (".exe" if os.name == "nt" else "")
    return os.path.join(DIST, name)


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller nao encontrado. Instale com:")
        print("    pip install pyinstaller")
        return 1

    print(f"Empacotando {config.TITLE}")
    print(f"  plataforma: {sys.platform}   python: {sys.version.split()[0]}")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", SPEC, "--noconfirm",
         "--distpath", DIST, "--workpath", WORK],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("\nFalha ao empacotar.")
        return result.returncode

    target = binary_path()
    if not os.path.isfile(target):
        print(f"\nO empacotador terminou, mas {target} nao existe.")
        return 1
    print(f"\nPronto: {target}  ({os.path.getsize(target) / 1024 / 1024:.1f} MB)")

    print("\nRodando o autoteste dentro do binario...")
    if subprocess.run([target, "--selftest"], cwd=ROOT).returncode != 0:
        print("O autoteste do binario FALHOU — veja save/selftest.log.")
        return 1
    print("\nAutoteste do binario ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
