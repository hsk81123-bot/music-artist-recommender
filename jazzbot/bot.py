"""텔레그램 봇 명령어 처리: /today, /random, /history.

    python -m jazzbot.bot          # 롱 폴링으로 계속 실행 (서버/PC용)
    python -m jazzbot.bot --once   # 쌓인 명령만 처리하고 종료 (GitHub Actions 주기 실행용)

처리한 update offset은 data/bot_state.json에 저장해 같은 명령을 두 번 처리하지 않는다.
허용된 chat(TELEGRAM_CHAT_ID, TELEGRAM_ALLOWED_CHAT_IDS)에서 온 명령에만 응답한다.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from .config import load_settings, setup_logging
from .formatter import render, render_history
from .service import JazzService
from .telegram import PermanentTelegramError, TelegramClient

log = logging.getLogger("jazzbot.bot")

COMMANDS = [
    ("today", "오늘의 아티스트 다시 보기"),
    ("random", "지금 바로 랜덤 아티스트 소개"),
    ("history", "최근 7일 소개 목록"),
    ("help", "도움말"),
]
HELP = "🎷 <b>Daily Jazz 봇</b>\n\n" + "\n".join(f"/{c} — {d}" for c, d in COMMANDS)


def load_offset(path) -> int | None:
    try:
        return json.loads(path.read_text()).get("offset")
    except (FileNotFoundError, ValueError):
        return None


def save_offset(path, offset: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"offset": offset}) + "\n")


class Bot:
    def __init__(self, service: JazzService, tg: TelegramClient):
        self.service = service
        self.tg = tg
        self.allowed = service.settings.allowed_chat_ids

    def handle(self, update: dict) -> None:
        msg = update.get("message") or {}
        text = (msg.get("text") or "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if not text.startswith("/") or not chat_id:
            return
        if self.allowed and chat_id not in self.allowed:
            log.warning("허용되지 않은 chat %s의 명령 무시: %s", chat_id, text)
            return
        command = text.split()[0][1:].split("@")[0].lower()
        log.info("명령 수신 chat=%s: /%s", chat_id, command)

        if command == "today":
            self.cmd_today(chat_id)
        elif command == "random":
            self.cmd_random(chat_id)
        elif command == "history":
            self.tg.send_message(chat_id, render_history(self.service.history.recent_daily(7)))
        elif command in ("start", "help"):
            self.tg.send_message(chat_id, HELP)
        else:
            self.tg.send_message(chat_id, "알 수 없는 명령이에요.\n\n" + HELP)

    def cmd_today(self, chat_id: str) -> None:
        h = self.service.history
        entry = h.for_date(self.service.today())
        if entry is None:
            last = h.last_daily()
            if last is None:
                self.tg.send_message(chat_id, "아직 소개한 아티스트가 없어요. /random 으로 먼저 들어보세요!")
                return
            self.tg.send_message(chat_id, "오늘 소개는 아직 발송 전이에요. 가장 최근 소개를 보여드릴게요.")
            entry = last
        self.tg.send_message(chat_id, *render(entry))

    def cmd_random(self, chat_id: str) -> None:
        self.tg.send_message(chat_id, "🎲 아티스트를 고르고 소개글을 쓰는 중이에요… 잠시만요!")
        entry = self.service.build_entry(self.service.pick_random(), "random", self.service.today())
        self.tg.send_message(chat_id, *render(entry))
        self.service.history.add(entry)
        self.service.history.save()

    def process(self, updates: list[dict], state_path) -> None:
        for update in updates:
            try:
                self.handle(update)
            except PermanentTelegramError as exc:
                log.error("응답 실패(건너뜀): %s", exc)
            except Exception:
                log.exception("명령 처리 중 오류(건너뜀)")
            # 실패한 명령도 offset을 넘겨 무한 반복을 막는다
            save_offset(state_path, update["update_id"] + 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily Jazz 봇 명령 처리")
    parser.add_argument("--once", action="store_true", help="쌓인 업데이트만 처리하고 종료")
    args = parser.parse_args(argv)

    setup_logging()
    settings = load_settings()
    if not settings.telegram_bot_token:
        log.error("TELEGRAM_BOT_TOKEN이 필요합니다.")
        return 2
    tg = TelegramClient(settings.telegram_bot_token)
    bot = Bot(JazzService(settings), tg)
    state = settings.bot_state_path

    try:
        tg.set_my_commands([(c, d) for c, d in COMMANDS])
    except Exception as exc:
        log.warning("명령어 메뉴 등록 실패(무시): %s", exc)

    if args.once:
        bot.process(tg.get_updates(load_offset(state), timeout=0), state)
        return 0

    log.info("롱 폴링 시작 (Ctrl+C로 종료)")
    while True:
        try:
            bot.process(tg.get_updates(load_offset(state), timeout=50), state)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            log.error("폴링 오류: %s — 10초 후 재시도", exc)
            time.sleep(10)


if __name__ == "__main__":
    sys.exit(main())
