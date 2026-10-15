# -*- mode: python ; coding: utf-8 -*-
"""Receita do PyInstaller para o Quebrando Tijolos.

Gera **um arquivo** com o jogo, os sprites e os sons dentro. O `save/` nao entra:
ele e criado ao lado do executavel na primeira execucao (ver `config._save_root`).

Rodar com:  pyinstaller quebrando_tijolos.spec --noconfirm

`console` esta False para o jogo abrir sem a janela preta atras. Se precisar ver
mensagens de erro em tempo real (depurando um problema), troque para True: o
`main.py` grava o traceback em `save/crash.log` de qualquer forma.
"""

import os
import sys

from PyInstaller.building.build_main import Analysis, EXE, PYZ

PROJECT_ROOT = os.path.abspath(os.getcwd())

datas = [
    (os.path.join(PROJECT_ROOT, "assets"), "assets"),
    (os.path.join(PROJECT_ROOT, "sounds"), "sounds"),
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Nada disso e usado pelo jogo, e cada um engorda o pacote.
    excludes=[
        "tkinter", "unittest", "pydoc", "doctest", "test", "distutils",
        "email", "html", "http", "xmlrpc", "pdb", "sqlite3",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="QuebrandoTijolos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
