import json
import random
from collections import Counter

import pytest

from jazzbot.artists import ERA_KO, INSTRUMENT_KO, choose_next, load_artists
from jazzbot.bot import Bot
from jazzbot.config import ROOT, load_settings
from jazzbot.formatter import render, render_history
from jazzbot.service import JazzService
from jazzbot.writer import DescriptionWriter, fallback_description
from jazzbot.youtube import TrackLinker, normalize, pick_best, video_id_from_url

ARTISTS = load_artists(ROOT / "data" / "artists.json")


def test_curation_is_large_and_balanced():
    assert len(ARTISTS) >= 100
    eras = Counter(a["era"] for a in ARTISTS)
    insts = Counter(a["instrument"] for a in ARTISTS)
    assert set(eras) == set(ERA_KO) and min(eras.values()) >= 10
    assert set(insts) == set(INSTRUMENT_KO) and min(insts.values()) >= 10
    assert len({a["id"] for a in ARTISTS}) == len(ARTISTS)
    for a in ARTISTS:
        for t in a["tracks"]:
            assert t["title"] and t["album"] and 1920 <= t["year"] <= 2026


def test_full_cycle_has_no_duplicates_and_avoids_repeats():
    rng = random.Random(42)
    used, prev, order = set(), None, []
    for _ in range(len(ARTISTS)):
        a = choose_next(ARTISTS, used, prev, rng)
        assert a["id"] not in used
        order.append(a)
        used.add(a["id"])
        prev = a
    assert len(order) == len(ARTISTS)
    same_era = sum(x["era"] == y["era"] for x, y in zip(order, order[1:]))
    same_inst = sum(x["instrument"] == y["instrument"] for x, y in zip(order, order[1:]))
    # 순환 막바지 남은 후보가 적을 때만 완화가 일어나야 한다
    assert same_era <= 3 and same_inst <= 3
    # 처음 80%는 엄격히 지켜져야 한다
    head = order[: int(len(order) * 0.8)]
    assert all(x["era"] != y["era"] and x["instrument"] != y["instrument"] for x, y in zip(head, head[1:]))


class FakeWriter:
    def write(self, artist):
        d = fallback_description(artist)
        d["track_points"] = [f"point {i}" for i in range(3)]
        return d


class FakeLinker:
    def find(self, artist, track):
        return None if track["title"].startswith("B") else "https://music.youtube.com/watch?v=abcdefghijk"


def fake_resolve(titles):
    out = {}
    for t in titles:
        if t == "Missing Page":
            out[t] = None
        else:
            out[t] = {"en_title": t, "en_url": "https://en.wikipedia.org/wiki/" + t.replace(" ", "_"),
                      "ko_title": "마일스 데이비스" if t == "Miles Davis" else None,
                      "ko_url": "https://ko.wikipedia.org/wiki/x" if t == "Miles Davis" else None}
    return out


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("jazzbot.service.safe_resolve", fake_resolve)
    monkeypatch.setenv("JAZZBOT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JAZZBOT_ARTISTS_FILE", str(ROOT / "data" / "artists.json"))
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    return JazzService(load_settings(), writer=FakeWriter(), linker=FakeLinker())


def test_service_cycles_and_restarts(service):
    seen = set()
    for i in range(len(ARTISTS)):
        artist, cycle = service.pick_daily(f"day-{i}")
        assert cycle == 1 and artist["id"] not in seen
        seen.add(artist["id"])
        service.history.add({"date": f"day-{i}", "kind": "daily", "artist_id": artist["id"], "cycle": cycle})
    artist, cycle = service.pick_daily("next")
    assert cycle == 2


def test_pick_is_deterministic_per_day(service):
    assert service.pick_daily("2026-10-12")[0]["id"] == service.pick_daily("2026-10-12")[0]["id"]


def test_render_marks_missing_links_and_buttons(service):
    artist = next(a for a in ARTISTS if a["id"] == "miles-davis")
    entry = service.build_entry(artist, "daily", "2026-10-12", 1)
    text, buttons = render(entry)
    assert "Miles Davis" in text and "10월 12일 (월)" in text
    assert "링크 없음" in text  # "Blue in Green"
    assert len(buttons) == 3 and buttons[0][0]["text"].startswith("▶ ①")  # 곡 2개 + 위키
    assert "이 곡부터 들어보세요" in text and "So What" in text
    assert len(text) <= 4096
    assert "Miles Davis" in render_history([entry])


def test_html_is_escaped(service):
    artist = dict(next(a for a in ARTISTS if a["id"] == "lambert-hendricks-and-ross"))
    entry = service.build_entry(artist, "daily", "2026-10-12", 1)
    text, _ = render(entry)
    assert "Lambert, Hendricks &amp; Ross" in text


def test_writer_without_key_falls_back():
    d = DescriptionWriter(None, "claude-opus-5-5").write(ARTISTS[0])
    assert d["generated_by"] == "template" and len(d["track_points"]) == 3


def test_matching():
    assert normalize("So What (Remastered 2009)") == "so what"
    cands = [("aaaaaaaaaaa", "So What?", "Some Cover Band"), ("bbbbbbbbbbb", "So What", "Miles Davis")]
    assert pick_best(cands, "So What", ["Miles Davis"]) == "bbbbbbbbbbb"
    assert pick_best([("c" * 11, "Totally Different", "Nobody")], "So What", ["Miles Davis"]) is None
    yt_title = [("d" * 11, "Miles Davis - So What (Official Audio)", "Miles Davis - Topic")]
    assert pick_best(yt_title, "So What", ["Miles Davis"]) == "d" * 11
    assert video_id_from_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_linker_falls_back_to_youtube_api(monkeypatch):
    class BrokenYT:
        def search(self, *a, **k):
            raise ConnectionError("blocked")

    linker = TrackLinker("KEY", ytmusic=BrokenYT())
    monkeypatch.setattr("jazzbot.retry.time.sleep", lambda s: None)
    monkeypatch.setattr(linker, "_youtube_api_request", lambda q: [
        {"id": {"videoId": "x" * 11}, "snippet": {"title": "So What", "channelTitle": "Miles Davis - Topic"}}
    ])
    url = linker.find({"name": "Miles Davis"}, {"title": "So What"})
    assert url == "https://music.youtube.com/watch?v=" + "x" * 11


class FakeTG:
    def __init__(self):
        self.sent = []

    def send_message(self, chat_id, text, buttons=None):
        self.sent.append((chat_id, text, buttons))


def test_bot_commands(service, tmp_path):
    tg = FakeTG()
    bot = Bot(service, tg)
    upd = lambda uid, chat, text: {"update_id": uid, "message": {"chat": {"id": chat}, "text": text}}
    state = tmp_path / "state.json"
    bot.process([upd(1, 111, "/today"), upd(2, 999, "/random"), upd(3, 111, "/random@DailyJazzBot"),
                 upd(4, 111, "/history")], state)
    assert json.loads(state.read_text())["offset"] == 5
    assert all(chat == "111" for chat, *_ in tg.sent)  # 999는 무시
    assert "아직 소개한 아티스트가 없어요" in tg.sent[0][1]
    assert "랜덤 재즈 아티스트" in tg.sent[2][1]
    assert service.history.entries[-1]["kind"] == "random"
    assert "아직 발송 기록이 없어요" in tg.sent[3][1]  # random은 history 목록에 안 나옴


def test_bot_ignores_everyone_without_allowed_chats(service, tmp_path):
    tg = FakeTG()
    bot = Bot(service, tg)
    bot.allowed = frozenset()
    bot.process([{"update_id": 1, "message": {"chat": {"id": 5}, "text": "/random"}}], tmp_path / "s.json")
    assert tg.sent == []


def test_bot_main_skips_polling_without_chat_id(monkeypatch):
    from jazzbot import bot as botmod

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
    monkeypatch.setattr(botmod, "TelegramClient", lambda *a: pytest.fail("getUpdates를 호출하면 안 됨"))
    assert botmod.main(["--once"]) == 0


def test_story_and_wiki_in_message(service):
    artist = next(a for a in ARTISTS if a["id"] == "miles-davis")
    text, buttons = render(service.build_entry(artist, "daily", "2026-10-12", 1))
    assert "📖 <b>흥미로운 이야기</b>" in text and "첫 테이크" in text
    assert 'href="https://en.wikipedia.org/wiki/Kind_of_Blue">Wikipedia: Kind of Blue</a>' in text
    assert ">한국어</a> · <a" in text  # 한국어판이 있으면 함께 표시
    assert buttons[-1][0]["url"] == "https://ko.wikipedia.org/wiki/x"


def test_missing_story_page_falls_back_to_artist_page(service):
    artist = json.loads(json.dumps(next(a for a in ARTISTS if a["id"] == "bill-frisell")))
    artist["story"]["wiki"] = "Missing Page"
    entry = service.build_entry(artist, "daily", "2026-10-12", 1)
    assert entry["story"]["link"]["url"].endswith("/Bill_Frisell")


def test_old_entries_without_story_still_render():
    entry = json.load(open(ROOT / "examples" / "sample_entry.json"))
    entry.pop("story", None), entry.pop("wiki", None)
    text, _ = render(entry)
    assert "Miles Davis" in text and "흥미로운 이야기" not in text


def test_wiki_resolve_parses_api(monkeypatch):
    from jazzbot import wiki

    monkeypatch.setattr(wiki, "_query", lambda titles: {
        "normalized": [{"from": "miles davis", "to": "Miles davis"}],
        "redirects": [{"from": "Miles davis", "to": "Miles Davis"}],
        "pages": [
            {"title": "Miles Davis", "langlinks": [{"lang": "ko", "title": "마일스 데이비스"}]},
            {"title": "Jim Hall", "pageprops": {"disambiguation": ""}},
            {"title": "Nope", "missing": True},
        ],
    })
    r = wiki.resolve(["miles davis", "Jim Hall", "Nope"])
    assert r["miles davis"]["ko_url"] == "https://ko.wikipedia.org/wiki/%EB%A7%88%EC%9D%BC%EC%8A%A4_%EB%8D%B0%EC%9D%B4%EB%B9%84%EC%8A%A4"
    assert r["miles davis"]["en_url"] == "https://en.wikipedia.org/wiki/Miles_Davis"
    assert r["Jim Hall"] is None and r["Nope"] is None
