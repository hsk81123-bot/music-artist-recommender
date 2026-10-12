"""Telegram Bot API 최소 클라이언트 (requests 사용)."""
from __future__ import annotations

import logging

import requests

from .retry import retry

log = logging.getLogger(__name__)


class TelegramError(Exception):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class PermanentTelegramError(Exception):
    """재시도해도 해결되지 않는 오류(잘못된 chat_id, HTML 파싱 오류 등)."""


class TelegramClient:
    def __init__(self, token: str):
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        self.base = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()

    def _call(self, method: str, payload: dict, timeout: float = 30) -> dict:
        try:
            resp = self.session.post(f"{self.base}/{method}", json=payload, timeout=timeout)
        except requests.RequestException as exc:
            # 예외 메시지에 토큰이 들어간 URL이 섞이지 않도록 감싼다
            raise TelegramError(f"{method} 네트워크 오류: {type(exc).__name__}") from None
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code == 429:
            retry_after = data.get("parameters", {}).get("retry_after", 5)
            raise TelegramError(f"{method} rate limited", retry_after=retry_after)
        if resp.status_code >= 500:
            raise TelegramError(f"{method} 서버 오류 {resp.status_code}")
        if not data.get("ok"):
            # 400/403 등은 재시도해도 같은 결과 → 즉시 실패
            raise PermanentTelegramError(f"{method} 실패: {data.get('description', resp.status_code)}")
        return data["result"]

    @retry(attempts=4, base_delay=2, exceptions=(TelegramError,))
    def send_message(self, chat_id: str | int, text: str, buttons: list[list[dict]] | None = None) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        result = self._call("sendMessage", payload)
        log.info("텔레그램 전송 완료 chat_id=%s message_id=%s", chat_id, result.get("message_id"))
        return result

    @retry(attempts=3, base_delay=2, exceptions=(TelegramError,))
    def get_updates(self, offset: int | None, timeout: int = 0) -> list[dict]:
        payload = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        return self._call("getUpdates", payload, timeout=timeout + 15)

    def set_my_commands(self, commands: list[tuple[str, str]]) -> None:
        self._call("setMyCommands", {
            "commands": [{"command": c, "description": d} for c, d in commands]
        })

