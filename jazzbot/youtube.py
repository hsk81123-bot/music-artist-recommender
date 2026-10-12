"""대표곡의 YouTube Music 링크 검색과 (선택) 'Daily Jazz' 플레이리스트 관리.

검색 순서: ytmusicapi(비공식, 키 불필요) → 실패/불일치 시 YouTube Data API v3.
어느 쪽에서도 못 찾으면 None을 돌려주고, 메시지에는 "링크 없음"으로 표시된다.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from difflib import SequenceMatcher

import requests

from .retry import retry

log = logging.getLogger(__name__)

YTM_WATCH = "https://music.youtube.com/watch?v={}"
YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

_NOISE = re.compile(
    r"\((?:[^)]*(?:remaster|version|live|take|mono|stereo|edit|official|audio|video|feat)[^)]*)\)"
    r"|\[[^\]]*\]"
    r"|\s-\s.*(?:remaster|version|live|take|mono|stereo).*$",
    re.IGNORECASE,
)


_GENERIC = {"the", "and", "trio", "quartet", "quintet", "sextet", "band", "orchestra", "group",
            "experiment", "brothers", "bros", "lifetime", "new", "fellowship", "s", "crisol"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _NOISE.sub(" ", text.lower())
    text = text.replace("&", " and ").replace("’", "'")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_score(wanted: str, found: str) -> float:
    w, f = normalize(wanted), normalize(found)
    if not w or not f:
        return 0.0
    if w == f:
        return 1.0
    # "Miles Davis - So What (Official Audio)" 같은 제목은 포함 관계로 판단
    if re.search(rf"\b{re.escape(w)}\b", f):
        return 0.9
    return SequenceMatcher(None, w, f).ratio()


def artist_matches(names: list[str], haystack: str) -> bool:
    hay = normalize(haystack)
    # "John Coltrane & Rashied Ali" → 각 사람 이름으로도 확인
    pieces = [p for name in names for p in re.split(r"\s+and\s+", normalize(name))]
    for n in pieces + [normalize(name) for name in names]:
        if not n:
            continue
        if n in hay:
            return True
        # "Bill Evans Trio"처럼 편성 이름이 붙으면 그 앞의 성(last name)만이라도 맞는지 본다
        words = [w for w in n.split() if w not in _GENERIC]
        if words and len(words[-1]) > 3 and re.search(rf"\b{re.escape(words[-1])}\b", hay):
            return True
    return False


def pick_best(candidates: list[tuple[str, str, str]], title: str, names: list[str]) -> str | None:
    """candidates: (video_id, 결과 제목, 아티스트/채널 문자열). 가장 그럴듯한 videoId를 고른다."""
    best_id, best = None, 0.0
    for vid, found_title, found_artist in candidates:
        if not vid:
            continue
        score = title_score(title, found_title)
        if artist_matches(names, f"{found_artist} {found_title}"):
            score += 0.3
        if score > best:
            best_id, best = vid, score
    # 제목이 충분히 비슷하고(0.75) 아티스트까지 맞으면 1.05 이상. 제목이 완전히 같으면 아티스트 불일치도 허용.
    return best_id if best >= 1.0 else None


class TrackLinker:
    def __init__(self, youtube_api_key: str | None = None, ytmusic=None):
        self.youtube_api_key = youtube_api_key
        self._ytmusic = ytmusic

    @property
    def ytmusic(self):
        if self._ytmusic is None:
            from ytmusicapi import YTMusic

            self._ytmusic = YTMusic()  # 검색은 인증 없이 가능
        return self._ytmusic

    def find(self, artist: dict, track: dict) -> str | None:
        names = [n for n in (track.get("performer"), artist["name"]) if n]
        query = f"{names[0]} {track['title']}"
        for source in (self._search_ytmusic, self._search_youtube_api):
            try:
                vid = source(query, track["title"], names)
            except Exception as exc:
                log.warning("%s 검색 실패 (%s): %s", source.__name__, query, exc)
                continue
            if vid:
                log.info("링크 찾음 [%s] %s → %s", source.__name__, query, vid)
                return YTM_WATCH.format(vid)
        log.warning("링크를 찾지 못함: %s", query)
        return None

    @retry(attempts=3, base_delay=2)
    def _search_ytmusic(self, query: str, title: str, names: list[str]) -> str | None:
        for filter_ in ("songs", "videos"):
            results = self.ytmusic.search(query, filter=filter_, limit=10)
            candidates = [
                (
                    r.get("videoId"),
                    r.get("title", ""),
                    " ".join(a.get("name", "") for a in r.get("artists") or []),
                )
                for r in results
            ]
            vid = pick_best(candidates, title, names)
            if vid:
                return vid
        return None

    def _search_youtube_api(self, query: str, title: str, names: list[str]) -> str | None:
        if not self.youtube_api_key:
            return None
        items = self._youtube_api_request(query)
        candidates = [
            (
                it.get("id", {}).get("videoId"),
                it.get("snippet", {}).get("title", ""),
                it.get("snippet", {}).get("channelTitle", ""),
            )
            for it in items
        ]
        return pick_best(candidates, title, names)

    @retry(attempts=3, base_delay=2, exceptions=(requests.RequestException,))
    def _youtube_api_request(self, query: str) -> list[dict]:
        resp = requests.get(
            YT_SEARCH_URL,
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "videoCategoryId": "10",  # Music
                "maxResults": 10,
                "key": self.youtube_api_key,
            },
            timeout=15,
        )
        if resp.status_code == 403:  # 할당량 초과·키 오류는 재시도해도 소용없다
            log.error("YouTube Data API 403: %s", resp.text[:200])
            return []
        resp.raise_for_status()
        return resp.json().get("items", [])


def video_id_from_url(url: str) -> str | None:
    m = re.search(r"[?&]v=([\w-]{11})", url or "")
    return m.group(1) if m else None


class PlaylistManager:
    """사용자 계정의 'Daily Jazz' 플레이리스트에 곡을 추가한다(선택 기능).

    YTMUSIC_AUTH_JSON에는 `ytmusicapi browser`(권장) 또는 `ytmusicapi oauth`로 만든
    JSON 파일 내용을 그대로 넣는다. OAuth 방식이면 클라이언트 ID/시크릿도 필요하다.
    """

    def __init__(self, auth_json: str, name: str, playlist_id: str | None = None,
                 client_id: str | None = None, client_secret: str | None = None):
        from ytmusicapi import YTMusic

        auth = json.loads(auth_json)
        kwargs = {}
        if "refresh_token" in auth:
            from ytmusicapi import OAuthCredentials

            if not (client_id and client_secret):
                raise ValueError("OAuth 인증에는 YTMUSIC_OAUTH_CLIENT_ID/SECRET가 필요합니다.")
            kwargs["oauth_credentials"] = OAuthCredentials(client_id=client_id, client_secret=client_secret)
        self.yt = YTMusic(auth, **kwargs)
        self.name = name
        self.playlist_id = playlist_id

    def ensure_playlist(self) -> str:
        if self.playlist_id:
            return self.playlist_id
        for pl in self.yt.get_library_playlists(limit=None):
            if pl.get("title") == self.name:
                self.playlist_id = pl["playlistId"]
                return self.playlist_id
        created = self.yt.create_playlist(
            self.name, "매일 아침 소개하는 재즈 아티스트의 대표곡 모음 (Daily Jazz bot)", privacy_status="PRIVATE"
        )
        if not isinstance(created, str):
            raise RuntimeError(f"플레이리스트 생성 실패: {created}")
        log.info("플레이리스트 '%s' 생성: %s", self.name, created)
        self.playlist_id = created
        return created

    @retry(attempts=3, base_delay=3)
    def add(self, video_ids: list[str]) -> None:
        if not video_ids:
            return
        playlist_id = self.ensure_playlist()
        result = self.yt.add_playlist_items(playlist_id, video_ids, duplicates=False)
        status = result.get("status") if isinstance(result, dict) else result
        log.info("플레이리스트에 %d곡 추가 요청 → %s", len(video_ids), status)
