"""매일 실행: 오늘의 아티스트를 골라 텔레그램으로 보내고 기록을 저장한다.

    python -m jazzbot.daily            # 오늘 분이 이미 있으면 건너뜀
    python -m jazzbot.daily --force    # 같은 날이라도 다시 선택·발송
    python -m jazzbot.daily --dry-run  # 발송·저장 없이 메시지만 출력
"""
from __future__ import annotations

import argparse
import logging
import sys

from .config import load_settings, setup_logging
from .formatter import render
from .service import JazzService
from .telegram import TelegramClient

log = logging.getLogger("jazzbot.daily")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily Jazz 발송")
    parser.add_argument("--dry-run", action="store_true", help="발송·저장 없이 메시지만 출력")
    parser.add_argument("--force", action="store_true", help="오늘 이미 보냈어도 새로 보냄")
    parser.add_argument("--date", help="기준 날짜(YYYY-MM-DD), 기본은 오늘(KST)")
    args = parser.parse_args(argv)

    setup_logging()
    settings = load_settings()
    service = JazzService(settings)
    date = args.date or service.today()

    if not args.force and service.history.for_date(date):
        log.info("%s 분은 이미 발송했습니다. (--force로 재발송)", date)
        return 0

    if not args.dry_run and not (settings.telegram_bot_token and settings.telegram_chat_id):
        log.error("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID가 필요합니다.")
        return 2

    artist, cycle = service.pick_daily(date)
    entry = service.build_entry(artist, "daily", date, cycle)
    if not args.dry_run:
        service.add_to_playlist(entry)

    text, buttons = render(entry)
    if args.dry_run:
        print(text)
        print("\n[buttons]", *(b[0]["text"] + " → " + b[0]["url"] for b in buttons), sep="\n")
        return 0

    try:
        TelegramClient(settings.telegram_bot_token).send_message(settings.telegram_chat_id, text, buttons)
    except Exception as exc:
        log.error("텔레그램 발송 실패: %s", exc)
        return 1

    service.history.add(entry)
    service.history.save()
    log.info("기록 저장 완료: %s (cycle %d)", artist["name"], cycle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
