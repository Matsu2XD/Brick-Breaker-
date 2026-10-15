"""Ponto de entrada do jogo.

    python main.py              jogar
    python main.py --version    mostrar a versao

O mesmo arquivo e o alvo do PyInstaller, entao ele precisa funcionar tanto
rodando do codigo quanto dentro do executavel.
"""

from __future__ import annotations

import os
import sys
import traceback

try:
    from src import config
except ModuleNotFoundError as missing:
    print(f"Dependencia ausente: {missing.name}")
    print("Instale com:  pip install -r requirements.txt")
    raise SystemExit(1) from None


def _write_crash_log() -> str:
    """Grava o traceback num arquivo e devolve o caminho.

    Num pacote sem console uma excecao nao aparece em lugar nenhum, e o jogo
    simplesmente "nao abre". O arquivo e a unica pista que o jogador tem para
    relatar o problema.
    """
    report = traceback.format_exc()
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        path = os.path.join(config.SAVE_DIR, "crash.log")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"\n--- {config.TITLE} ---\n{report}\n")
        return path
    except OSError:
        return "(nao foi possivel gravar o log)"


def _selftest() -> int:
    """Confere que o pacote carrega tudo o que precisa, sem abrir janela.

    Existe porque um executavel sem console nao mostra erro nenhum: se um sprite
    ou um som ficar de fora do pacote, o jogo simplesmente nao abre e o jogador
    nao tem o que reportar. Este modo escreve um relatorio em ``save/`` e devolve
    um codigo de saida, entao da para verificar o pacote automaticamente.
    """
    import os

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    lines: list[str] = []
    problems: list[str] = []

    def report(label: str, ok: bool, detail: str = "") -> None:
        lines.append(f"[{'ok  ' if ok else 'FALHA'}] {label} {detail}")
        if not ok:
            problems.append(label)

    def note(label: str, detail: str = "") -> None:
        lines.append(f"[info ] {label} {detail}")

    note("titulo", config.TITLE)
    note("pacote congelado", str(getattr(sys, "frozen", False)))
    note("executavel", sys.executable)
    report("raiz de recursos", os.path.isdir(config.PROJECT_ROOT), config.PROJECT_ROOT)
    report("pasta de sons", os.path.isdir(config.SOUND_DIR), config.SOUND_DIR)
    report("pasta de gravacao", os.access(config.SAVE_DIR, os.W_OK), config.SAVE_DIR)

    import pygame

    pygame.mixer.pre_init(config.SOUND_SAMPLE_RATE, -16, 2, 512)
    pygame.init()
    # `convert_alpha` exige um modo de video definido, e sem ele o atlas nao
    # carrega. Uma janela de 1x1 basta, e o driver dummy nao mostra nada.
    pygame.display.set_mode((1, 1))

    from src.audio import SoundBank
    from src.sprites import SpriteSheet

    sheet = SpriteSheet()
    sheet.load()
    report("atlas de sprites", sheet.available and len(sheet.frames) == 61,
           f"{len(sheet.frames)} recortados")
    report("tijolo da linha 0", sheet.brick_pair(0, (78, 26))[0] is not None)
    report("bola", sheet.ball(22) is not None)
    report("coracao e estrela", sheet.heart() is not None and sheet.star() is not None)

    bank = SoundBank()
    report("mixer", bank.available)
    report("efeitos ligados", not bank.missing, f"{len(bank.sounds)} eventos")
    report("trilha encontrada", bank.music_available,
           os.path.basename(bank.music_path or "-"))

    from src.settings import Settings

    settings = Settings()
    report("ajustes gravaveis", settings.save(), config.SETTINGS_FILE)
    report("ajustes recarregaveis", Settings.load().sfx_volume == settings.sfx_volume)

    from src.controls import InputState
    from src.game import Game

    game = Game(seed=7)
    report("o jogo abre no menu", game.state.name == "MENU", game.state.name)
    report("grade montada", len(game.bricks) == 77, f"{len(game.bricks)} tijolos")
    game.start_new_game()
    game._handle_launch_key()
    for _ in range(120):
        game.advance(1 / 60, InputState(move=0.3))
    game.draw()
    report("120 quadros simulados", game.state.name == "PLAYING" or game.score > 0,
           f"pontos={game.score}")
    report("sprites aplicados no jogo", game.ball_sprite is not None)
    game.shutdown()

    text = "\n".join(lines)
    print(text)
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(os.path.join(config.SAVE_DIR, "selftest.log"), "w",
                  encoding="utf-8") as handle:
            handle.write(text + "\n")
    except OSError:
        pass

    if problems:
        print(f"\n{len(problems)} PROBLEMAS: {problems}")
        return 1
    print("\nautoteste ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if "--version" in arguments or "-V" in arguments:
        print(config.TITLE)
        return 0
    if "--selftest" in arguments:
        return _selftest()

    from src.game import Game

    game = Game()
    try:
        game.run()
    except KeyboardInterrupt:
        pass
    except Exception:  # noqa: BLE001 — ultimo recurso: registrar e sair limpo
        where = _write_crash_log()
        print(traceback.format_exc())
        print(f"Detalhes em: {where}")
        return 1
    finally:
        game.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
