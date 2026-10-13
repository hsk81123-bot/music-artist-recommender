"""위키백과 링크 확인.

큐레이션 JSON에는 영문 위키백과 문서 제목만 들어 있다. 발송 시 Wikipedia API로
문서가 실제로 있는지(동음이의 문서가 아닌지) 확인하고, 한국어판이 있으면 함께 찾는다.

    python -m jazzbot.wiki    # 큐레이션의 모든 위키 제목 검증 (CI용)
"""
from __future__ import annotations

import logging
import sys
from urllib.parse import quote

import requests

from .retry import retry

log = logging.getLogger(__name__)

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "DailyJazzBot/1.0 (https://github.com/hsk81123-bot/music-artist-recommender)"}


def page_url(lang: str, title: str) -> str:
    return f"https://{lang}.wikipedia.org/wiki/" + quote(title.replace(" ", "_"), safe="_()'!,")


def fallback(title: str) -> dict:
    """API를 쓸 수 없을 때: 검증 없이 영문 링크만 만든다(제목은 CI에서 검증됨)."""
    return {"en_title": title, "en_url": page_url("en", title), "ko_title": None, "ko_url": None}


@retry(attempts=3, base_delay=2, exceptions=(requests.RequestException,))
def _query(titles: list[str]) -> dict:
    resp = requests.get(API, params={
        "action": "query", "format": "json", "formatversion": 2, "redirects": 1,
        "titles": "|".join(titles),
        "prop": "langlinks|pageprops", "lllang": "ko", "ppprop": "disambiguation",
    }, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()["query"]


def resolve(titles: list[str]) -> dict[str, dict | None]:
    """영문 제목 → {en_title, en_url, ko_title, ko_url}. 없는 문서·동음이의 문서는 None."""
    out: dict[str, dict | None] = {}
    unique = list(dict.fromkeys(t for t in titles if t))
    for i in range(0, len(unique), 50):  # API는 한 번에 50개까지
        batch = unique[i:i + 50]
        q = _query(batch)
        alias = {}
        for kind in ("normalized", "redirects"):
            for m in q.get(kind, []):
                alias[m["from"]] = m["to"]
        pages = {p["title"]: p for p in q.get("pages", [])}
        for t in batch:
            final = t
            while final in alias:
                final = alias[final]
            p = pages.get(final)
            if not p or p.get("missing") or p.get("invalid") or "disambiguation" in p.get("pageprops", {}):
                out[t] = None
                continue
            ko = next((ll["title"] for ll in p.get("langlinks", []) if ll.get("lang") == "ko"), None)
            out[t] = {
                "en_title": final, "en_url": page_url("en", final),
                "ko_title": ko, "ko_url": page_url("ko", ko) if ko else None,
            }
    return out


def safe_resolve(titles: list[str]) -> dict[str, dict | None]:
    try:
        return resolve(titles)
    except Exception as exc:  # 위키 확인 실패가 발송을 막지 않도록
        log.warning("위키백과 확인 실패, 검증 없이 링크를 만듭니다: %s", exc)
        return {t: fallback(t) for t in titles if t}


def main() -> int:
    from .artists import load_artists
    from .config import load_settings, setup_logging

    setup_logging()
    artists = load_artists(load_settings().artists_path)
    titles = [t for a in artists for t in (a["wiki"], a["story"]["wiki"])]
    result = resolve(titles)
    bad = sorted({t for t, r in result.items() if r is None})
    ko = sum(1 for a in artists if result.get(a["wiki"]) and result[a["wiki"]]["ko_url"])
    print(f"아티스트 {len(artists)}명 · 위키 제목 {len(result)}개 확인 · 한국어판 있는 아티스트 {ko}명")
    for t in bad:
        users = [a["id"] for a in artists if t in (a["wiki"], a["story"]["wiki"])]
        print(f"::error::위키 문서 없음/동음이의: {t!r} ← {', '.join(users)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
