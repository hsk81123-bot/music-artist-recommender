# 📰 데일리 뉴스 텔레그램 봇 — 새 세션용 템플릿

Daily Jazz 봇과 같은 구조(텔레그램 발송 + GitHub Actions 스케줄 + 저장소에 기록 커밋)로 **분야별 뉴스 봇**을 만들 때 쓰는 프롬프트입니다.

## 사용법

1. GitHub에 **빈 저장소**를 하나 만듭니다(예: `daily-news-bot`). README만 있는 상태면 충분합니다.
2. 그 저장소로 Claude Code 새 세션을 엽니다.
3. 아래 **「프롬프트」** 블록 전체를 복사해 붙여 넣습니다. `{{ }}` 자리만 채우면 됩니다. 이 파일 끝의 [예시 주제 설정](#예시-주제-설정-그대로-붙여-넣어도-됨)을 그대로 써도 됩니다.
4. 세션이 끝나면 아래 [설치 체크리스트](#설치-체크리스트-세션이-끝난-뒤-직접-할-일) 순서대로 설정합니다.

> **봇을 여러 개 만들 때**: 주제마다 저장소를 따로 만들기보다 **저장소 하나에 주제를 설정 파일로 추가**하는 방식을 권합니다. 코드와 스케줄은 하나만 관리하고, 주제마다 다른 텔레그램 봇이나 대화방으로 보낼 수 있습니다. 아래 프롬프트도 이 방식으로 작성했습니다.

---

## 프롬프트

````markdown
# 프로젝트: 분야별 데일리 뉴스 텔레그램 봇

## 목표
매일 정해진 시간({{발송 시각, 예: 오전 7시 KST}})에 주제별 최신 뉴스를 골라 텔레그램으로 보내는 프로그램을 만들어줘.
주제마다 메시지를 따로 보내고, 주제는 설정 파일(`config/topics.yaml`)에 항목을 추가하는 것만으로 늘릴 수 있게 해줘.

## 주제 설정
`config/topics.yaml`에 아래 주제를 넣어줘. 주제마다 이름, 이모지, 검색어(한국어/영어), 추가 RSS 피드(선택),
보낼 기사 수, 보낼 텔레그램 대화방을 정할 수 있어야 해.

{{주제 목록 — 이 파일 끝의 "예시 주제 설정"을 붙여 넣거나 직접 작성}}

## 기능 요구사항
1. 뉴스 수집
   - 기본 소스는 Google News RSS 검색(API 키 불필요)으로 해줘.
     한국어: `https://news.google.com/rss/search?q=<검색어>&hl=ko&gl=KR&ceid=KR:ko`
     영어:   `https://news.google.com/rss/search?q=<검색어>&hl=en-US&gl=US&ceid=US:en`
   - 주제별로 추가 RSS 피드(언론사, arXiv 등)를 더할 수 있게 해줘.
   - 최근 {{24}}시간 안의 기사만 쓰고, 기사가 부족하면 기간을 {{72}}시간까지 늘려줘.
   - 같은 기사가 여러 언론사·검색어로 중복되면 하나만 남겨줘(정규화한 URL과 제목 유사도로 판단).
   - 이전에 보낸 기사(URL)는 다시 보내지 않도록 기록해줘.
2. 기사 선정
   - 주제별로 {{5}}개를 고르되, 한 언론사가 독점하지 않게 출처를 섞어줘.
   - ANTHROPIC_API_KEY가 있으면 Claude가 후보 중 중요도가 높은 기사를 고르고, 없으면 최신순과 출처 다양성으로 골라줘.
3. 요약 (한국어)
   - ANTHROPIC_API_KEY가 있으면 기사마다 2~3줄 요약과, 주제별 "오늘의 한 줄 정리"를 Claude로 만들어줘.
   - 요약은 RSS에서 받은 제목과 설명문만 근거로 쓰고, 거기 없는 사실은 지어내지 않게 해줘. 기사 본문을 통째로 옮기지 마.
   - 키가 없거나 API가 실패하면 제목·출처·시간·링크만으로 보내고, 발송은 계속 진행해줘.
4. 텔레그램
   - HTML 형식으로 꾸미고, 기사마다 제목(링크), 출처, 발행 시각(KST), 요약을 넣어줘. 기사별 "원문 보기" 인라인 버튼도 달아줘.
   - 주제마다 다른 봇 토큰이나 chat_id로 보낼 수 있게 해줘(설정에서 환경변수 이름을 지정하고, 없으면 기본값을 사용).
   - 봇 명령어: /today(오늘 보낸 뉴스 다시 보기), /now <주제>(지금 바로 수집해서 보내기), /topics(주제 목록), /history(최근 7일).
5. 스케줄링과 기록
   - GitHub Actions cron으로 매일 {{발송 시각}}에 실행해줘. 로컬/서버 cron 설정 방법도 README에 넣어줘.
   - 발송 기록(보낸 기사 URL, 날짜, 주제)은 저장소의 `data/history.json`에 저장하고 워크플로가 커밋하게 해줘.
     기록이 너무 커지지 않게 {{60}}일이 지난 항목은 정리해줘.

## 기술 조건
- Python 3.11+, Claude 모델은 기본 claude-opus-5-5(환경변수 CLAUDE_MODEL로 변경 가능)
- 키(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ANTHROPIC_API_KEY 등)는 .env / GitHub Secrets로 관리하고 하드코딩 금지
- 네트워크 오류·API 실패 시 재시도와 로그 출력. 한 주제나 한 피드가 실패해도 나머지는 계속 발송
- `--dry-run`(발송·저장 없이 출력), `--topic <이름>`(한 주제만), `--force`(오늘 이미 보냈어도 다시 수집·발송) 옵션

## 이전 프로젝트에서 배운 점 (반드시 반영)
- TELEGRAM_CHAT_ID가 비어 있으면 봇 명령 처리는 아무에게도 응답하지 말고 getUpdates도 호출하지 마
  (호출하면 메시지가 읽음 처리되어 사용자가 브라우저로 chat_id를 확인할 수 없게 됨).
- 봇 명령은 허용된 chat_id에서 온 것에만 응답해(모르는 사람이 /now를 반복해 API 비용을 쓰지 않게).
- 텔레그램 "chat not found" 오류는 사용자가 봇에게 Start를 누르지 않았거나 chat_id가 틀린 경우라고 로그에 안내해줘.
- 워크플로는 기록을 커밋하므로 `permissions: contents: write`와 `concurrency` 그룹을 설정하고, push 전에 `git pull --rebase`로 재시도해줘.
  `git add`는 아직 없는 파일 때문에 실패하지 않게 `git add -A data/`로 해줘.
- GitHub cron은 몇 분~수십 분 늦게 시작하므로 원하는 시각보다 10분 일찍 예약해줘(07:00 KST → `50 21 * * *` UTC).
- 봇 명령 폴링 워크플로는 비공개 저장소에서 무료 사용 시간을 많이 쓰니 기본 간격을 1시간으로 하고, README에 사용량을 적어줘.
- 개발 환경(샌드박스)에서는 외부 네트워크가 막혀 있을 수 있으니, 네트워크 호출은 모두 모킹한 단위 테스트로 검증하고
  실제 동작은 GitHub Actions에서 workflow_dispatch로 실행한 뒤 로그를 읽어 확인해줘.
- 수동 실행 버튼은 기본 브랜치(main)에 있는 워크플로에만 생기니, 첫 실행 전에 main 머지가 필요하다고 안내해줘.

## 결과물
- 전체 소스 코드와 폴더 구조, `config/topics.yaml`
- 단위 테스트(pytest)와 테스트 워크플로
- README: BotFather 봇 생성, chat_id 확인(봇에게 Start 누르기 포함), GitHub Secrets와 Workflow permissions 설정,
  주제 추가 방법, 로컬/서버 cron 설정까지 단계별 설치 가이드
- 실제 발송 메시지 예시 1개
````

---

## 예시 주제 설정 (그대로 붙여 넣어도 됨)

요청하신 다섯 분야를 예시로 채웠습니다. 프롬프트의 `{{주제 목록}}` 자리에 붙여 넣으세요. 검색어는 Google News 검색 문법(`OR`, 따옴표)을 따릅니다. 첫 실행 결과를 보고 조정하면 됩니다.

```markdown
| 주제 | 이모지 | 한국어 검색어 | 영어 검색어 | 추가 소스 | 기사 수 |
|---|---|---|---|---|---|
| 주식 | 📈 | 코스피 OR 코스닥 OR 증시 OR "미국 증시" | "stock market" OR Nasdaq OR "S&P 500" | — | 5 |
| 부동산 | 🏠 | 부동산 OR 아파트값 OR 청약 OR 주택담보대출 OR 전세 | — (국내 위주) | — | 5 |
| AI | 🤖 | 인공지능 OR "생성형 AI" OR LLM | "AI model" OR OpenAI OR Anthropic OR "Google DeepMind" | — | 5 |
| 배터리 | 🔋 | 2차전지 OR 배터리 OR LG에너지솔루션 OR 삼성SDI OR SK온 OR 에코프로 | "EV battery" OR "lithium-ion" OR "solid-state battery" | — | 5 |
| 배터리 모델링 | 🧮 | "배터리 모델링" OR "배터리 시뮬레이션" OR "배터리 디지털 트윈" OR BMS | "battery modeling" OR "battery simulation" OR "battery digital twin" OR PyBaMM OR "battery management system" | arXiv: `http://export.arxiv.org/api/query?search_query=abs:%22battery%20model%22&sortBy=submittedDate&sortOrder=descending&max_results=20` | 3 |

- 주제마다 메시지를 따로 보냅니다(하루 5개 메시지).
- 모든 주제를 같은 대화방(TELEGRAM_CHAT_ID)으로 보냅니다. 나중에 주제별로 대화방을 나누고 싶으면 설정에서 chat_id 환경변수 이름만 바꿉니다.
- "배터리 모델링"은 뉴스 기사가 적은 분야라 기간을 7일(168시간)까지 늘리고, arXiv 최신 논문을 별도 섹션 "📄 최신 논문"으로 붙여줘.
```

**검색어 팁**
- 너무 넓으면 광고성·중복 기사가 많아집니다. 기업명이나 전문 용어를 섞어 범위를 좁히세요.
- "배터리 모델링"처럼 좁은 분야는 뉴스가 거의 없는 날이 많습니다. 그래서 arXiv 같은 논문 소스를 함께 쓰거나, 수집 기간을 늘리고 "새 소식 없음"이라고 보내도록 하는 게 좋습니다.
- 주식처럼 기사가 많은 분야는 Claude 키가 있을 때 중요도 선별 효과가 큽니다. 키가 없으면 최신순으로 골라서 잡다한 기사가 섞일 수 있습니다.

---

## 설치 체크리스트 (세션이 끝난 뒤 직접 할 일)

Daily Jazz 봇을 세팅하면서 실제로 막혔던 지점 순서대로 정리했습니다.

1. **텔레그램 봇 만들기**: @BotFather → `/newbot` → 토큰을 복사합니다. 토큰은 채팅에 붙여 넣지 마세요.
   - 기존 Daily Jazz 봇을 같이 써도 됩니다. 봇 하나로 여러 주제를 보낼 수 있습니다. 주제별로 봇을 따로 두고 싶을 때만 새로 만드세요.
2. **봇에게 Start 누르기**: 텔레그램에서 새 봇을 검색해 대화를 열고 **시작(Start)** 버튼을 누릅니다. 이걸 안 하면 발송할 때 `chat not found` 오류가 납니다.
3. **chat_id 확인**: `https://api.telegram.org/bot<토큰>/getUpdates`를 열어 `"chat":{"id":…}`의 숫자를 확인합니다. 결과가 `[]`이면 봇에게 메시지를 한 번 더 보내고 새로고침하세요. @userinfobot으로 내 ID를 확인해도 됩니다. Daily Jazz와 같은 대화방으로 받으려면 기존 chat_id를 그대로 쓰면 됩니다.
4. **GitHub Secrets 등록**: Settings → Secrets and variables → Actions에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 넣습니다. 있으면 `ANTHROPIC_API_KEY`도 넣습니다.
5. **쓰기 권한 켜기**: Settings → Actions → General → Workflow permissions → **Read and write permissions**.
6. **PR 머지**: 수동 실행 버튼과 예약 실행은 main 브랜치의 워크플로에만 적용됩니다.
7. **첫 실행**: Actions 탭 → 발송 워크플로 → **Run workflow**. 실패하면 로그를 Claude에게 보여 주세요. 세션에서 직접 실행하고 로그를 읽어 달라고 해도 됩니다.

**Anthropic API 키 메모**: Claude 구독(Pro/Max)과 API는 결제가 따로입니다. [console.anthropic.com](https://console.anthropic.com)에서 키를 만들고 크레딧을 충전해야 합니다. 키가 없어도 제목과 링크 위주로 발송은 됩니다. 뉴스 요약은 기사 수만큼 호출이 늘어나니, 비용이 걱정되면 `CLAUDE_MODEL=claude-haiku-5-5`로 바꾸는 방법도 있습니다.
