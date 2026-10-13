"""Claude API로 한국어 소개 문장을 생성한다.

사실 정보(이름, 활동 시기, 악기, 대표곡·앨범·연도)는 큐레이션 JSON에서 오고,
Claude는 설명 문장(소개, 감상 포인트, 입문 추천 이유)만 작성한다.
API가 실패하거나 응답이 이상하면 템플릿 문장으로 대체해 발송은 계속된다.
"""
from __future__ import annotations

import json
import logging

from .artists import ERA_KO

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """너는 재즈를 사랑하는 한국어 음악 칼럼니스트다. 매일 아침 텔레그램으로 재즈 아티스트 한 명을 소개하는 글을 쓴다.

규칙:
- 아티스트의 기본 정보와 대표곡 목록(곡명·앨범·연도)은 사용자 메시지에 주어진 것이 정확한 사실이다. 이 값을 바꾸거나 다른 곡을 추가하지 마라.
- 소개(intro)는 3~4문장: 음악적 특징과 재즈사에서의 의의를 담는다. 사용자 메시지의 '별도 소개되는 일화'는 메시지에 따로 실리므로 intro에서 반복하지 않는다.
- 사실은 널리 기록된 것만 쓴다. 확실하지 않은 숫자·날짜·인용은 쓰지 말고, 애매하면 일반적인 서술로 대신한다.
- track_points는 대표곡 순서 그대로 곡마다 한 줄(40자 안팎)의 감상 포인트: 어느 부분을 귀 기울여 들으면 좋은지.
- starter_reason은 입문자가 왜 그 곡부터 들으면 좋은지 1~2문장.
- 친근하지만 과장되지 않은 존댓말(~요/~습니다)을 쓰고, 마크다운이나 HTML 태그는 쓰지 않는다. 인명·곡명은 영문 그대로 둔다."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "intro": {"type": "string"},
        "track_points": {"type": "array", "items": {"type": "string"}},
        "starter_reason": {"type": "string"},
    },
    "required": ["intro", "track_points", "starter_reason"],
    "additionalProperties": False,
}


def _artist_brief(artist: dict) -> str:
    starter = artist["tracks"][artist["starter"]]
    lines = [
        f"이름: {artist['name']}",
        f"활동 시기: {artist['active']}",
        f"주 악기: {artist['instrument_detail']}",
        f"시대: {ERA_KO[artist['era']]}",
        f"스타일: {artist['style']}",
        "대표곡:",
    ]
    for i, t in enumerate(artist["tracks"], 1):
        by = f" (연주: {t['performer']})" if t.get("performer") else ""
        lines.append(f"  {i}. {t['title']} — {t['album']}, {t['year']}{by}")
    lines.append(f"입문 추천곡: {starter['title']}")
    if artist.get("story"):
        lines.append(f"별도 소개되는 일화(반복 금지): {artist['story']['text']}")
    return "\n".join(lines)


def fallback_description(artist: dict) -> dict:
    """Claude를 쓸 수 없을 때의 기본 문장."""
    era = ERA_KO[artist["era"]]
    return {
        "intro": (
            f"{artist['name']}은(는) {era} 시대를 대표하는 {artist['instrument_detail']} 아티스트로, "
            f"{artist['style']} 스타일로 잘 알려져 있습니다. 오늘은 대표곡 세 곡으로 그 음악 세계를 만나 보세요."
        ),
        "track_points": ["" for _ in artist["tracks"]],
        "starter_reason": "아티스트의 개성이 가장 잘 드러나는 곡이라 첫 감상으로 좋습니다.",
        "generated_by": "template",
    }


class DescriptionWriter:
    def __init__(self, api_key: str | None, model: str):
        self.model = model
        self.client = None
        if api_key:
            import anthropic

            # SDK가 429/5xx/네트워크 오류를 지수 백오프로 재시도한다.
            self.client = anthropic.Anthropic(api_key=api_key, max_retries=4, timeout=120)

    def write(self, artist: dict) -> dict:
        if self.client is None:
            log.warning("ANTHROPIC_API_KEY가 없어 템플릿 문장을 사용합니다.")
            return fallback_description(artist)
        try:
            return self._call_claude(artist)
        except Exception as exc:  # 발송은 계속되어야 하므로 모든 실패를 템플릿으로 대체
            log.error("Claude 소개 생성 실패, 템플릿으로 대체: %s", exc)
            return fallback_description(artist)

    def _call_claude(self, artist: dict) -> dict:
        import anthropic

        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": "다음 아티스트의 오늘자 소개를 작성해 주세요.\n\n" + _artist_brief(artist),
                }],
                output_config={
                    "effort": "medium",
                    "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
                },
                # 안전 분류기가 요청을 거절하면 서버가 권장 모델로 자동 재시도한다.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.APIStatusError as exc:
            log.error("Claude API 오류 status=%s request_id=%s", exc.status_code, exc.request_id)
            raise

        if response.stop_reason == "refusal":
            raise RuntimeError(f"Claude가 요청을 거절했습니다: {response.stop_details}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("응답이 max_tokens에서 잘렸습니다.")

        text = "".join(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
        points = [str(p).strip() for p in data["track_points"]]
        if len(points) != len(artist["tracks"]):
            log.warning("감상 포인트 개수 불일치(%d) — 길이를 맞춥니다.", len(points))
            points = (points + [""] * 3)[: len(artist["tracks"])]
        log.info("Claude 소개 생성 완료 (model=%s, out_tokens=%s)", response.model, response.usage.output_tokens)
        return {
            "intro": data["intro"].strip(),
            "track_points": points,
            "starter_reason": data["starter_reason"].strip(),
            "generated_by": response.model,
        }
