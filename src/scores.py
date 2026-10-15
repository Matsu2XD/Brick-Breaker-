"""Placar de lideres, persistido entre sessoes.

O placar guarda as melhores pontuacoes junto da fase alcancada, porque sozinhos os
pontos nao dizem se a partida foi boa: 4.000 pontos na fase 2 e melhor que 4.000
pontos na fase 5.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass

from src import config, store


@dataclass
class ScoreEntry:
    score: int = 0
    level: int = 1
    date: str = ""

    @classmethod
    def from_raw(cls, raw: object) -> "ScoreEntry | None":
        if not isinstance(raw, dict):
            return None
        score, level = raw.get("score"), raw.get("level", 1)
        if isinstance(score, bool) or not isinstance(score, int) or score < 0:
            return None
        if isinstance(level, bool) or not isinstance(level, int) or level < 1:
            level = 1
        date = raw.get("date")
        return cls(score=score, level=level,
                   date=date if isinstance(date, str) else "")


@dataclass
class Leaderboard:
    entries: list[ScoreEntry]

    @classmethod
    def load(cls) -> "Leaderboard":
        raw = store.load(config.SCORES_FILE, {"scores": []})
        scores = raw.get("scores")
        if not isinstance(scores, list):
            scores = []
        entries = [entry for entry in (ScoreEntry.from_raw(item) for item in scores)
                   if entry is not None]
        entries.sort(key=lambda entry: (-entry.score, entry.level))
        return cls(entries=entries[:config.SCORES_KEPT])

    def save(self) -> bool:
        return store.save(config.SCORES_FILE,
                          {"scores": [asdict(entry) for entry in self.entries]})

    @property
    def best(self) -> int:
        return self.entries[0].score if self.entries else 0

    def qualifies(self, score: int) -> bool:
        if score <= 0:
            return False
        if len(self.entries) < config.SCORES_KEPT:
            return True
        return score > self.entries[-1].score

    def submit(self, score: int, level: int,
               today: str | None = None) -> int:
        """Insere a pontuacao e devolve a posicao (1-based), ou 0 se nao entrou."""
        if not self.qualifies(score):
            return 0
        stamp = today or datetime.date.today().isoformat()
        entry = ScoreEntry(score=score, level=level, date=stamp)
        self.entries.append(entry)
        self.entries.sort(key=lambda item: (-item.score, item.level))
        del self.entries[config.SCORES_KEPT:]
        self.save()
        return self.entries.index(entry) + 1

    def clear(self) -> None:
        self.entries.clear()
        self.save()
