"""발송 기록 항목(entry)을 텔레그램 HTML 메시지 + 인라인 버튼으로 변환한다."""
from __future__ import annotations

from html import escape as _escape


def escape(text: str) -> str:
    """텔레그램 HTML 모드용 이스케이프(<, >, &만 필요)."""
    return _escape(str(text), quote=False)

NUM = ["①", "②", "③", "④", "⑤"]
WEEKDAY_KO = "월화수목금토일"


def _date_label(date: str) -> str:
    from datetime import date as _d

    d = _d.fromisoformat(date)
    return f"{d.month}월 {d.day}일 ({WEEKDAY_KO[d.weekday()]})"


def render(entry: dict) -> tuple[str, list[list[dict]]]:
    a = entry["artist"]
    header = "🎷 <b>오늘의 재즈 아티스트</b>" if entry["kind"] == "daily" else "🎲 <b>랜덤 재즈 아티스트</b>"
    lines = [
        f"{header} · {_date_label(entry['date'])}",
        "",
        f"<b>{escape(a['name'])}</b>",
        f"🗓 활동 시기: {escape(a['active'])}",
        f"🎹 주 악기: {escape(a['instrument_detail'])}",
        f"🎼 장르/스타일: {escape(a['era_ko'])} · {escape(a['style'])}",
        "",
        escape(entry["intro"]),
        "",
        "🎧 <b>대표곡</b>",
    ]
    buttons: list[list[dict]] = []
    for i, t in enumerate(entry["tracks"]):
        n = NUM[i]
        by = f" · {escape(t['performer'])}" if t.get("performer") else ""
        lines.append(f"{n} <b>{escape(t['title'])}</b>")
        album = "싱글" if t["album"] == "Single" else escape(t["album"])
        lines.append(f"   💿 {album} ({t['year']}){by}")
        if t.get("point"):
            lines.append(f"   ✨ {escape(t['point'])}")
        if t.get("url"):
            lines.append(f"   ▶ <a href=\"{_escape(t['url'])}\">YouTube Music에서 듣기</a>")
            title = t["title"] if len(t["title"]) <= 24 else t["title"][:23] + "…"
            label = f"▶ {n} {title} · YouTube Music에서 듣기"
            buttons.append([{"text": label, "url": t["url"]}])
        else:
            lines.append("   ▶ 링크 없음")
        lines.append("")

    s = entry["starter"]
    starter_track = entry["tracks"][s["index"]]
    lines += [
        f"🔰 <b>이 곡부터 들어보세요:</b> {escape(starter_track['title'])}",
        escape(s["reason"]),
    ]
    if entry.get("playlist_url"):
        lines += ["", f"📂 <a href=\"{_escape(entry['playlist_url'])}\">Daily Jazz 플레이리스트</a>"]
    text = "\n".join(lines)
    if len(text) > 4096:  # 텔레그램 메시지 길이 제한
        text = text[:4090] + "…"
    return text, buttons


def render_history(entries: list[dict]) -> str:
    if not entries:
        return "아직 발송 기록이 없어요."
    lines = ["📜 <b>최근 소개한 아티스트</b>", ""]
    for e in reversed(entries):
        a = e["artist"]
        lines.append(f"• {_date_label(e['date'])} — <b>{escape(a['name'])}</b> ({escape(a['era_ko'])}, {escape(a['instrument_detail'])})")
    return "\n".join(lines)
