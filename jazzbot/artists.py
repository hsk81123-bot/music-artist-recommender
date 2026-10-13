"""큐레이션 목록 로드와 '오늘의 아티스트' 선택 로직."""
from __future__ import annotations

import json
import random
from pathlib import Path

ERA_KO = {
    "swing": "스윙",
    "bebop": "비밥",
    "cool": "쿨 재즈",
    "hardbop": "하드밥",
    "modal": "모달 재즈",
    "free": "프리 재즈",
    "fusion": "퓨전",
    "contemporary": "현대 재즈",
}

INSTRUMENT_KO = {
    "saxophone": "색소폰",
    "trumpet": "트럼펫",
    "piano": "피아노",
    "vocal": "보컬",
    "bass": "베이스",
    "drums": "드럼",
    "guitar": "기타",
}


def load_artists(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        artists = json.load(f)["artists"]
    for a in artists:
        if a["era"] not in ERA_KO or a["instrument"] not in INSTRUMENT_KO:
            raise ValueError(f"알 수 없는 era/instrument: {a['id']}")
        if len(a["tracks"]) != 3 or not 0 <= a["starter"] < 3:
            raise ValueError(f"대표곡은 3곡, starter는 0~2여야 합니다: {a['id']}")
    return artists


def choose_next(
    artists: list[dict],
    used_ids: set[str],
    previous: dict | None,
    rng: random.Random,
) -> dict:
    """아직 소개하지 않은 아티스트 중 하나를 고른다.

    - used_ids: 이번 순환(cycle)에서 이미 소개한 아티스트. 비어 있지 않은 후보가 없으면
      호출 측에서 새 순환을 시작해야 한다.
    - previous: 직전에 소개한 아티스트. 같은 시대·같은 악기가 연속되지 않도록
      ① 시대와 악기 모두 다름 → ② 악기만 다름 → ③ 시대만 다름 → ④ 아무나 순으로 완화한다.
    - 남은 아티스트가 많은 시대에 가중치를 줘서 순환 후반에 특정 시대만 몰리지 않게 한다.
    """
    remaining = [a for a in artists if a["id"] not in used_ids]
    if not remaining:
        raise ValueError("남은 아티스트가 없습니다 — 새 순환을 시작하세요.")

    candidates = remaining
    if previous:
        tiers = [
            lambda a: a["era"] != previous["era"] and a["instrument"] != previous["instrument"],
            lambda a: a["instrument"] != previous["instrument"],
            lambda a: a["era"] != previous["era"],
        ]
        for cond in tiers:
            filtered = [a for a in remaining if cond(a)]
            if filtered:
                candidates = filtered
                break

    era_left: dict[str, int] = {}
    for a in remaining:
        era_left[a["era"]] = era_left.get(a["era"], 0) + 1
    era_size: dict[str, int] = {}
    for a in candidates:
        era_size[a["era"]] = era_size.get(a["era"], 0) + 1
    # 시대 선택 확률 ∝ 그 시대의 남은 인원 → 시대 안에서는 균등.
    weights = [era_left[a["era"]] / era_size[a["era"]] for a in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]
