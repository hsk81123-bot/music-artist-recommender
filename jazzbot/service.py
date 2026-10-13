"""아티스트 선택 → 소개 생성 → 링크 검색 → 기록 항목 생성까지의 공통 흐름."""
from __future__ import annotations

import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from .artists import ERA_KO, choose_next, load_artists
from .config import Settings
from .history import History
from .writer import DescriptionWriter
from .youtube import PlaylistManager, TrackLinker, video_id_from_url

log = logging.getLogger(__name__)


class JazzService:
    def __init__(self, settings: Settings, writer: DescriptionWriter | None = None,
                 linker: TrackLinker | None = None):
        self.settings = settings
        self.artists = load_artists(settings.artists_path)
        self.by_id = {a["id"]: a for a in self.artists}
        self.history = History(settings.history_path)
        self.writer = writer or DescriptionWriter(settings.anthropic_api_key, settings.claude_model)
        self.linker = linker or TrackLinker(settings.youtube_api_key)

    def now(self) -> datetime:
        return datetime.now(ZoneInfo(self.settings.timezone))

    def today(self) -> str:
        return self.now().date().isoformat()

    # ---- 선택 ----
    def pick_daily(self, date: str) -> tuple[dict, int]:
        cycle = self.history.current_cycle()
        used = self.history.used_in_cycle(cycle) & set(self.by_id)
        if len(used) >= len(self.artists):
            cycle += 1
            used = set()
            log.info("모든 아티스트를 소개했습니다. 새 순환(cycle %d)을 시작합니다.", cycle)
        last = self.history.last_daily()
        previous = self.by_id.get(last["artist_id"]) if last else None
        rng = random.Random(f"{date}:{cycle}")  # 같은 날 재실행해도 같은 선택
        return choose_next(self.artists, used, previous, rng), cycle

    def pick_random(self) -> dict:
        return random.choice(self.artists)

    # ---- 내용 생성 ----
    def build_entry(self, artist: dict, kind: str, date: str, cycle: int | None = None) -> dict:
        log.info("아티스트: %s (%s / %s)", artist["name"], artist["era"], artist["instrument"])
        desc = self.writer.write(artist)
        tracks = []
        for track, point in zip(artist["tracks"], desc["track_points"]):
            url = self.linker.find(artist, track)
            tracks.append({**track, "point": point, "url": url})
        entry = {
            "date": date,
            "kind": kind,
            "artist_id": artist["id"],
            "artist": {
                "name": artist["name"],
                "active": artist["active"],
                "instrument_detail": artist["instrument_detail"],
                "era": artist["era"],
                "era_ko": ERA_KO[artist["era"]],
                "style": artist["style"],
            },
            "intro": desc["intro"],
            "tracks": tracks,
            "starter": {"index": artist["starter"], "reason": desc["starter_reason"]},
            "generated_by": desc.get("generated_by"),
        }
        if cycle is not None:
            entry["cycle"] = cycle
        return entry

    # ---- 플레이리스트 (선택) ----
    def add_to_playlist(self, entry: dict) -> None:
        s = self.settings
        if not s.playlist_enabled:
            return
        try:
            pm = PlaylistManager(s.ytmusic_auth_json, s.playlist_name, s.ytmusic_playlist_id,
                                 s.ytmusic_oauth_client_id, s.ytmusic_oauth_client_secret)
            ids = [v for v in (video_id_from_url(t["url"]) for t in entry["tracks"]) if v]
            pm.add(ids)
            entry["playlist_url"] = f"https://music.youtube.com/playlist?list={pm.ensure_playlist()}"
        except Exception as exc:  # 선택 기능이므로 실패해도 발송은 계속
            log.error("플레이리스트 추가 실패(무시하고 계속): %s", exc)
