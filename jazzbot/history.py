"""발송 기록(data/history.json) 관리.

각 항목은 메시지를 다시 그릴 수 있는 전체 내용을 담아서 /today가 API를 다시 호출하지 않게 한다.
kind == "daily"인 항목만 중복 방지 순환(cycle)에 포함되고, /random 결과는 "random"으로 기록된다.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class History:
    def __init__(self, path: Path):
        self.path = path
        self.entries: list[dict] = []
        if path.exists():
            with open(path, encoding="utf-8") as f:
                self.entries = json.load(f).get("entries", [])

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 원자적 저장: 중간에 죽어도 기존 파일이 깨지지 않게 한다.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"entries": self.entries}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, self.path)

    def add(self, entry: dict) -> None:
        self.entries.append(entry)

    @property
    def daily(self) -> list[dict]:
        return [e for e in self.entries if e.get("kind") == "daily"]

    def for_date(self, date: str) -> dict | None:
        for e in reversed(self.daily):
            if e["date"] == date:
                return e
        return None

    def last_daily(self) -> dict | None:
        daily = self.daily
        return daily[-1] if daily else None

    def current_cycle(self) -> int:
        last = self.last_daily()
        return last.get("cycle", 1) if last else 1

    def used_in_cycle(self, cycle: int) -> set[str]:
        return {e["artist_id"] for e in self.daily if e.get("cycle", 1) == cycle}

    def recent_daily(self, n: int = 7) -> list[dict]:
        return self.daily[-n:]
