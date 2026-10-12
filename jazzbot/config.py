"""환경변수(.env / GitHub Secrets)에서 설정을 읽는다. 키는 코드에 하드코딩하지 않는다."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:  # python-dotenv는 로컬 실행 편의용(선택)
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # pragma: no cover
    pass


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or default


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    allowed_chat_ids: frozenset[str]
    anthropic_api_key: str | None
    claude_model: str
    youtube_api_key: str | None
    ytmusic_auth_json: str | None
    ytmusic_oauth_client_id: str | None
    ytmusic_oauth_client_secret: str | None
    ytmusic_playlist_id: str | None
    playlist_name: str
    timezone: str
    artists_path: Path
    history_path: Path
    bot_state_path: Path

    @property
    def playlist_enabled(self) -> bool:
        return bool(self.ytmusic_auth_json)


def load_settings() -> Settings:
    data_dir = Path(_env("JAZZBOT_DATA_DIR", str(ROOT / "data")))
    chat_id = _env("TELEGRAM_CHAT_ID")
    extra = _env("TELEGRAM_ALLOWED_CHAT_IDS", "") or ""
    allowed = {c.strip() for c in extra.split(",") if c.strip()}
    if chat_id:
        allowed.add(chat_id)
    return Settings(
        telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=chat_id,
        allowed_chat_ids=frozenset(allowed),
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        claude_model=_env("CLAUDE_MODEL", "claude-opus-5-5"),
        youtube_api_key=_env("YOUTUBE_API_KEY"),
        ytmusic_auth_json=_env("YTMUSIC_AUTH_JSON"),
        ytmusic_oauth_client_id=_env("YTMUSIC_OAUTH_CLIENT_ID"),
        ytmusic_oauth_client_secret=_env("YTMUSIC_OAUTH_CLIENT_SECRET"),
        ytmusic_playlist_id=_env("YTMUSIC_PLAYLIST_ID"),
        playlist_name=_env("YTMUSIC_PLAYLIST_NAME", "Daily Jazz"),
        timezone=_env("JAZZBOT_TIMEZONE", "Asia/Seoul"),
        artists_path=Path(_env("JAZZBOT_ARTISTS_FILE", str(data_dir / "artists.json"))),
        history_path=data_dir / "history.json",
        bot_state_path=data_dir / "bot_state.json",
    )


def setup_logging() -> None:
    logging.basicConfig(
        level=_env("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    # 서드파티 라이브러리의 과도한 로그는 줄인다.
    for noisy in ("httpx", "urllib3", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
