# 🎷 Daily Jazz — 매일 아침 재즈 아티스트 한 명을 소개하는 텔레그램 봇

매일 오전 7시(KST) 무렵에 재즈 아티스트 한 명을 골라 **소개 · 대표곡 3곡 · YouTube Music 링크**를 텔레그램으로 보내 줍니다.

- **111명**의 큐레이션 목록: 시대 8개(스윙, 비밥, 쿨, 하드밥, 모달, 프리, 퓨전, 현대 재즈) × 악기 7개(색소폰, 트럼펫, 피아노, 보컬, 베이스, 드럼, 기타)
- 목록을 다 돌기 전까지는 같은 아티스트가 다시 나오지 않고, 시대나 악기가 전날과 겹치지 않게 고릅니다.
- 사실 정보(이름, 활동 시기, 악기, 곡명·앨범·연도)는 JSON에서 가져오고, **Claude는 설명 문장만** 씁니다.
- 아티스트마다 직접 정리한 **흥미로운 이야기** 하나와 관련 위키백과 링크, 그리고 **아티스트 위키백과 링크**(한국어판이 있으면 함께)를 붙입니다. 이 부분은 Anthropic 키가 없어도 나갑니다.
- ytmusicapi로 링크를 찾고, 실패하면 YouTube Data API v3로 다시 찾습니다. 그래도 없으면 "링크 없음"으로 표시하고 발송은 그대로 진행합니다.
- 봇 명령어: `/today`, `/random`, `/history`
- (선택) 내 YouTube Music 계정의 **"Daily Jazz"** 플레이리스트에 매일 곡을 자동으로 추가합니다.
- 정기 발송은 내 PC의 예약 작업으로 돌립니다(7번). 봇 명령 처리는 GitHub Actions에서 무료로 돌아갑니다.

---

## 📁 폴더 구조

```
.
├── jazzbot/
│   ├── config.py      # 환경변수(.env / GitHub Secrets) 로딩
│   ├── artists.py     # 큐레이션 로딩, 선택 로직(중복·연속 방지)
│   ├── history.py     # 발송 기록(data/history.json)
│   ├── writer.py      # Claude API로 한국어 소개문 생성(실패 시 템플릿)
│   ├── youtube.py     # ytmusicapi → YouTube Data API 대체 검색, 플레이리스트
│   ├── wiki.py        # 위키백과 문서 확인·한국어판 찾기 (python -m jazzbot.wiki 로 전체 검증)
│   ├── telegram.py    # Telegram Bot API 클라이언트(재시도 포함)
│   ├── formatter.py   # HTML 메시지와 인라인 버튼 만들기
│   ├── service.py     # 선택 → 생성 → 링크까지 공통 흐름
│   ├── daily.py       # 매일 발송 진입점  (python -m jazzbot.daily)
│   ├── bot.py         # 명령어 처리 진입점 (python -m jazzbot.bot)
│   └── retry.py       # 지수 백오프 재시도
├── scripts/
│   └── run_daily_local.sh  # 내 PC에서 정기 발송 (cron / 작업 스케줄러가 호출)
├── data/
│   ├── artists.json   # ★ 아티스트 큐레이션 (111명)
│   ├── history.json   # 발송 기록 (자동 갱신·커밋)
│   └── bot_state.json # 처리한 텔레그램 update offset (자동 생성)
├── examples/sample_entry.json   # 메시지 예시에 쓴 데이터
├── tests/test_jazzbot.py
├── .github/workflows/
│   ├── daily-jazz.yml    # 수동 실행용 (정기 발송은 내 PC에서)
│   ├── bot-commands.yml  # 30분마다 쌓인 봇 명령 처리
│   ├── verify-data.yml   # 큐레이션의 위키백과 제목 검증
│   └── tests.yml
├── requirements.txt
└── .env.example
```

---

## 🚀 설치 가이드

### 0. 로컬 준비 (Python 3.11 이상)

```bash
git clone https://github.com/<you>/music-artist-recommender.git
cd music-artist-recommender
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # 아래 단계를 따라 값을 채웁니다
```

### 1. 텔레그램 봇 만들기 (BotFather)

1. 텔레그램에서 **@BotFather**를 찾아 대화를 시작합니다.
2. `/newbot`을 보내고 봇 이름(예: `Daily Jazz`)과 사용자명(예: `my_daily_jazz_bot`, `bot`으로 끝나야 함)을 정합니다.
3. BotFather가 알려 주는 토큰(`123456789:AA...`)을 `.env`의 `TELEGRAM_BOT_TOKEN`에 넣습니다.
   > 토큰은 비밀번호와 같습니다. 코드나 공개 저장소에 올리지 마세요. 유출됐다면 BotFather에서 `/revoke`로 재발급하세요.
4. (선택) 명령어 메뉴는 봇이 처음 실행될 때 `setMyCommands`로 자동 등록됩니다. 직접 하려면 BotFather에서 `/setcommands`를 보내고 아래 내용을 붙여 넣으세요.
   ```
   today - 오늘의 아티스트 다시 보기
   random - 지금 바로 랜덤 아티스트 소개
   history - 최근 7일 소개 목록
   ```

### 2. chat_id 확인하기

**개인 채팅으로 받을 때**
1. 방금 만든 봇과 대화를 열고 `/start`(또는 아무 메시지)를 보냅니다.
2. 브라우저에서 아래 주소를 엽니다. `<TOKEN>` 자리에 토큰을 넣으세요.
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. 응답의 `"chat":{"id":123456789, ...}`에 있는 숫자가 chat_id입니다. `.env`의 `TELEGRAM_CHAT_ID`에 넣습니다.

**그룹에서 받을 때**: 봇을 그룹에 초대하고 그룹에 메시지를 하나 보낸 뒤 같은 방법으로 확인합니다. 그룹 ID는 `-100…`처럼 음수입니다.
**채널에서 받을 때**: 봇을 채널 관리자로 추가하고 채널에 글을 올린 뒤 `getUpdates`에서 `channel_post.chat.id`를 확인합니다.

> 결과가 `[]`라면 봇에게 메시지를 한 번 더 보내고 새로고침하세요. 웹훅을 설정해 둔 봇은 `getUpdates`가 동작하지 않으니 `deleteWebhook`을 먼저 호출해야 합니다.

봇 명령어는 `TELEGRAM_CHAT_ID`(그리고 `TELEGRAM_ALLOWED_CHAT_IDS`에 쉼표로 적은 chat)에서 온 것에만 응답합니다. 모르는 사람이 `/random`을 반복해 API 비용을 쓰는 일을 막기 위해서입니다.

### 3. API 키 준비

| 변수 | 필수 | 발급 방법 |
|---|---|---|
| `ANTHROPIC_API_KEY` | 권장 | [console.anthropic.com](https://console.anthropic.com) → API Keys. 없으면 소개문이 짧은 기본 템플릿으로 나갑니다. |
| `YOUTUBE_API_KEY` | 권장 | [Google Cloud Console](https://console.cloud.google.com) → 프로젝트 생성 → "YouTube Data API v3" 사용 설정 → 사용자 인증 정보 → API 키. 무료 할당량은 하루 10,000 단위이고 검색 한 번에 100 단위가 듭니다. ytmusicapi가 실패할 때만 쓰므로 보통 충분합니다. |

모델은 기본값 `claude-opus-5-5`를 씁니다. 바꾸려면 `CLAUDE_MODEL`을 설정하세요. 요청에는 서버 측 refusal fallback(`fallbacks: "default"`)이 켜져 있어서, 안전 분류기가 드물게 요청을 거절해도 권장 모델로 자동 재시도합니다.

### 4. (선택) YouTube Music 플레이리스트 자동 추가 — ytmusicapi 인증

링크 **검색**에는 인증이 필요 없습니다. 이 단계는 내 계정에 "Daily Jazz" 플레이리스트를 만들고 곡을 추가할 때만 필요합니다.

**방법 A. 브라우저 헤더 인증 (권장)**
1. 데스크톱 브라우저에서 [music.youtube.com](https://music.youtube.com)에 로그인합니다.
2. 개발자 도구(F12) → Network 탭을 열고 필터에 `browse`를 입력한 뒤, 라이브러리 등 아무 페이지나 클릭합니다.
3. `browse?...`로 시작하는 **POST** 요청을 선택해 Request Headers 전체를 복사합니다.
   - Firefox: 요청 우클릭 → Copy → Copy Request Headers
   - Chrome: Headers 탭의 Request Headers 부분을 "Raw"로 보고 `accept: */*`부터 끝까지 선택해 복사
4. 터미널에서 아래 명령을 실행하고 복사한 헤더를 붙여 넣습니다. (Linux/macOS는 Enter 후 Ctrl-D, Windows는 Ctrl-Z 후 Enter)
   ```bash
   ytmusicapi browser      # → browser.json 생성
   ```
5. 한 줄 JSON으로 바꿔서 `.env`의 `YTMUSIC_AUTH_JSON`이나 GitHub Secret에 넣습니다.
   ```bash
   python -c "import json;print(json.dumps(json.load(open('browser.json'))))"
   ```
   이 인증은 브라우저에서 로그아웃하기 전까지 유효합니다(보통 약 2년).

**방법 B. OAuth**
1. Google Cloud Console에서 YouTube Data API를 사용 설정하고, OAuth 클라이언트 ID를 **"TV 및 입력 제한 기기"** 유형으로 만듭니다.
2. `ytmusicapi oauth --client-id <ID> --client-secret <SECRET>`을 실행하고 안내에 따라 승인하면 `oauth.json`이 생깁니다.
3. `YTMUSIC_AUTH_JSON`에 oauth.json 내용을 넣고, `YTMUSIC_OAUTH_CLIENT_ID`와 `YTMUSIC_OAUTH_CLIENT_SECRET`도 설정합니다.

플레이리스트는 처음 실행할 때 **비공개**로 만들어집니다. 이미 있는 플레이리스트를 쓰려면 `YTMUSIC_PLAYLIST_ID`(URL의 `list=` 뒤 값)를 지정하세요. 플레이리스트 추가에 실패해도 텔레그램 발송은 계속됩니다.

> `browser.json`과 `oauth.json`은 `.gitignore`에 들어 있습니다. 절대 커밋하지 마세요.

### 5. 로컬에서 테스트

```bash
python -m jazzbot.daily --dry-run   # 발송·저장 없이 메시지를 터미널에 출력
python -m jazzbot.daily             # 실제 발송 + data/history.json 기록
python -m jazzbot.daily --force     # 오늘 이미 보냈어도 다시 발송
python -m jazzbot.bot               # 봇 명령어 응답(롱 폴링, Ctrl+C로 종료)
pip install -r requirements-dev.txt && pytest -q   # 단위 테스트
```

### 6. GitHub Actions로 매일 자동 실행 (무료)

1. 이 저장소를 내 GitHub 계정에 push합니다. 스케줄 워크플로는 **기본 브랜치**(main)에 있어야 동작합니다.
2. **Settings → Secrets and variables → Actions → New repository secret**에서 아래 값을 등록합니다.

   | Secret | 필수 |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | ✅ |
   | `TELEGRAM_CHAT_ID` | ✅ |
   | `ANTHROPIC_API_KEY` | 권장 |
   | `YOUTUBE_API_KEY` | 권장 |
   | `YTMUSIC_AUTH_JSON` | 선택 |
   | `YTMUSIC_OAUTH_CLIENT_ID`, `YTMUSIC_OAUTH_CLIENT_SECRET` | OAuth 방식일 때 |

   같은 화면의 **Variables** 탭에는 필요할 때만 `YTMUSIC_PLAYLIST_ID`, `TELEGRAM_ALLOWED_CHAT_IDS`를 등록합니다.
3. **Settings → Actions → General → Workflow permissions**를 **Read and write permissions**로 설정합니다. 워크플로가 `data/history.json`을 커밋해야 하기 때문입니다.
4. **Actions 탭 → Daily Jazz → Run workflow**로 한 번 수동 실행해서 메시지가 오는지 확인합니다.
5. 정기 발송은 GitHub가 아니라 **내 PC의 예약 작업**이 맡습니다. 아래 7번을 설정하세요. 이 단계에서는 수동 실행으로 충분합니다.

알아 두면 좋은 점:
- 정기 발송은 PC가 켜져 있어야 합니다. 꺼져 있던 동안의 발송은 PC를 켠 뒤 다음 실행 때 한 번에 채워집니다.
- `bot-commands.yml`은 30분마다 쌓인 `/today`, `/random`, `/history` 명령을 처리합니다. 응답이 늦을 수 있으니 즉시 응답이 필요하면 서버에서 `python -m jazzbot.bot`을 상시 실행하고, 이 워크플로는 Actions 탭에서 **Disable workflow**로 꺼 두세요(둘 다 켜 두면 명령을 서로 가져갑니다).
- 비공개 저장소는 Actions 무료 사용 시간이 월 2,000분입니다. 30분 간격 폴링은 월 약 1,440분을 쓰니, 부족하면 cron 간격을 `0 * * * *`(매시)로 늘리세요. 공개 저장소는 무제한입니다.
- 두 워크플로는 `concurrency: jazzbot-data`로 묶여 있어 기록 파일을 동시에 고치지 않습니다.

### 7. 정기 발송: 내 PC에서 실행 (권장 설정)

정기 발송은 `scripts/run_daily_local.sh`를 PC의 예약 작업으로 등록해서 돌립니다. 이 스크립트는 다음을 처리합니다.
- 오늘 이미 보냈으면 바로 끝나므로, 하루에 여러 번 호출해도 중복으로 나가지 않습니다.
- 발송 기록을 커밋해서 GitHub에 올립니다(`/today`, `/history` 명령이 이 기록을 씁니다).
- 로그는 `logs/daily.log`에 쌓입니다.

**준비 (한 번만)**
```bash
cd music-artist-recommender
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt     # Windows: .venv\Scripts\pip install -r requirements.txt
cp .env.example .env     # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, (선택) ANTHROPIC_API_KEY 입력
chmod +x scripts/run_daily_local.sh
scripts/run_daily_local.sh     # 지금 한 번 실행해서 메시지가 오는지 확인
```
`git push`를 쓰므로 이 PC에서 GitHub에 push할 수 있어야 합니다(HTTPS 로그인 또는 SSH 키).

**Linux / macOS**: `crontab -e`에 아래 두 줄을 추가합니다. 경로는 실제 위치로 바꾸세요.
```cron
# 7시부터 12시까지 매시간 확인(이미 보냈으면 바로 종료). 잠들었거나 꺼져 있던 경우도 다음 정각에 채워집니다.
0 7-12 * * * /home/me/music-artist-recommender/scripts/run_daily_local.sh
# 컴퓨터를 켤 때마다 한 번 실행해서, 꺼져 있던 동안 놓친 발송을 채웁니다.
@reboot /home/me/music-artist-recommender/scripts/run_daily_local.sh
```
> 시스템 시간대가 한국 시간이 아니면 `crontab` 시각을 그에 맞게 바꾸세요.

**Windows 작업 스케줄러**: "작업 만들기"로 작업을 하나 만듭니다.
- 트리거 1: 매일 **07:00**, 고급 설정에서 "반복 간격 1시간", "기간 6시간"
- 트리거 2: **사용자 로그온할 때**
- 동작: 프로그램 `C:\Program Files\Git\bin\bash.exe`, 인수 `-lc "/c/Users/me/music-artist-recommender/scripts/run_daily_local.sh"` (경로는 실제 위치, Git Bash 필요)
- 조건/설정: "예약된 시작 시간을 놓쳤으면 가능한 한 빨리 작업 시작", "작업을 실행하려면 컴퓨터 깨우기" 체크

**확인과 문제 해결**
- 로그: `logs/daily.log`. "종료 (코드 0)"이면 정상입니다.
- 이미 보낸 날 다시 보내려면 `.venv/bin/python -m jazzbot.daily --force`를 직접 실행하세요.
- 발송은 됐는데 GitHub에 기록이 안 올라갔다면 로그에 "발송 기록을 GitHub에 올리지 못했습니다"가 찍힙니다. 저장소에서 `git status`로 확인하세요.

**봇 명령어 상시 실행 (systemd)**: `/etc/systemd/system/daily-jazz-bot.service`
```ini
[Unit]
Description=Daily Jazz Telegram bot
After=network-online.target

[Service]
WorkingDirectory=/home/me/music-artist-recommender
ExecStart=/home/me/music-artist-recommender/.venv/bin/python -m jazzbot.bot
Restart=always
RestartSec=10
User=me

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now daily-jazz-bot
journalctl -u daily-jazz-bot -f    # 로그 확인
```


---

## ⚙️ 동작 방식

**아티스트 선택** (`jazzbot/artists.py`)
1. 이번 순환(cycle)에서 아직 소개하지 않은 아티스트만 후보로 둡니다. 111명을 모두 소개하면 cycle이 1 늘고 처음부터 다시 돕니다.
2. 전날과 **시대도 악기도 다른** 후보를 우선 고릅니다. 그런 후보가 없을 때만(순환 막바지) "악기만 다름", "시대만 다름" 순서로 조건을 풀어 줍니다.
3. 남은 인원이 많은 시대일수록 뽑힐 확률을 높여, 순환 후반에 특정 시대만 몰리지 않게 합니다.
4. 같은 날짜로 다시 실행하면 같은 아티스트가 나오고, 이미 보낸 날은 `--force` 없이는 건너뜁니다.

**소개문 생성** (`jazzbot/writer.py`): 큐레이션 JSON의 사실 정보를 Claude에게 넘기고 `intro`(3~4문장: 음악적 특징, 재즈사적 의의), `track_points`(곡별 감상 포인트), `starter_reason`(입문 추천 이유)만 JSON 스키마(structured outputs)로 받습니다. 곡명·앨범·연도는 메시지에 JSON 값이 그대로 들어가므로 모델이 바꿀 수 없습니다. API 오류, 거절, 형식 오류가 나면 템플릿 문장으로 대신 보냅니다.

**이야기와 위키백과** (`jazzbot/wiki.py`): 일화는 사실 확인이 중요해서 Claude가 지어내지 않고 큐레이션 JSON의 `story.text`를 그대로 씁니다. 발송할 때 Wikipedia API로 `wiki`(아티스트 문서)와 `story.wiki`(일화 관련 문서)가 실제로 있는지 확인하고, 한국어판이 있으면 한국어 링크를 우선 붙입니다. 관련 문서가 없으면 아티스트 문서로 대신하고, 위키백과 확인 자체가 실패해도 영문 링크를 만들어 발송은 계속합니다. `data/artists.json`을 고치면 `Verify curation` 워크플로가 모든 제목을 자동으로 검증합니다.

**링크 검색** (`jazzbot/youtube.py`): `"<연주자> <곡명>"`으로 ytmusicapi에서 songs, 다음으로 videos를 검색합니다. 제목 유사도와 아티스트 일치 여부로 점수를 매기고, 기준을 넘는 결과가 없으면 YouTube Data API로 다시 검색합니다. 둘 다 실패한 곡은 "링크 없음"으로 표시하고 버튼을 달지 않습니다. 찾은 videoId는 `https://music.youtube.com/watch?v=<id>`로 바꿔 붙입니다.

**실패 처리**: 텔레그램 요청은 429(`retry_after`를 따름)와 5xx, 네트워크 오류일 때 최대 4번 재시도하고, 400/403처럼 재시도해도 소용없는 오류는 바로 실패로 처리합니다. Anthropic SDK는 자체적으로 4번까지 재시도합니다. 텔레그램 발송까지 실패하면 기록을 남기지 않고 종료 코드 1로 끝나므로 Actions에 실패로 표시됩니다.

**기록** (`data/history.json`): 항목마다 메시지를 다시 그리는 데 필요한 내용이 모두 들어 있어서, `/today`는 API를 다시 부르지 않고 같은 메시지를 보여 줍니다. `/random` 결과는 `kind: "random"`으로 저장되며 순환과 `/history`에는 들어가지 않습니다.

### 큐레이션 수정하기

`data/artists.json`에 아래 형식으로 추가하거나 고치면 됩니다. `era`와 `instrument`는 정해진 키 중 하나여야 합니다.

```jsonc
{
  "id": "miles-davis",
  "name": "Miles Davis",
  "active": "1940s–1991",
  "instrument": "trumpet",              // saxophone|trumpet|piano|vocal|bass|drums|guitar
  "instrument_detail": "트럼펫",          // 메시지에 표시되는 악기명
  "era": "modal",                       // swing|bebop|cool|hardbop|modal|free|fusion|contemporary
  "style": "모달 재즈 (쿨·하드밥·퓨전 전반)",
  "tracks": [
    {"title": "So What", "album": "Kind of Blue", "year": 1959},
    {"title": "Pursuance", "album": "A Love Supreme", "year": 1965,
     "performer": "John Coltrane"}        // 리더가 다른 녹음이면 검색에 쓸 연주자명
  ],
  "starter": 0,                         // 입문 추천곡 인덱스(0~2)
  "wiki": "Miles Davis",                // 영문 위키백과 문서 제목
  "story": {
    "text": "1959년 Kind of Blue 녹음 날, ...",   // 메시지에 그대로 나가는 일화
    "wiki": "Kind of Blue"              // 일화 관련 영문 위키백과 문서 제목
  }
}
```

앨범명이 `"Single"`인 곡은 SP/싱글로 처음 나온 곡이고, 메시지에는 "싱글"로 표시됩니다. 발매 연도는 첫 발매(녹음이 아닌 발매) 기준입니다. 큐레이션은 직접 정리했지만 일부 발매 연도나 수록 앨범에 오류가 있을 수 있으니, 틀린 곳을 찾으면 JSON을 고쳐 주세요. 수정한 뒤에는 `pytest -q`로 형식을 검증하세요.

---

## 💬 실제 발송 메시지 예시

`examples/sample_entry.json`(Miles Davis)을 `jazzbot/formatter.py`로 렌더링한 결과입니다. 텔레그램에서는 아래처럼 보입니다. YouTube 링크 ID는 예시용 자리표시자이고, ③번은 링크를 찾지 못한 경우를 보여 줍니다. 한국어 위키백과 문서가 있는 아티스트는 위키백과 줄에 "한국어 · English"가 함께 나옵니다.

> 🎷 **오늘의 재즈 아티스트** · 10월 12일 (월)
>
> **Miles Davis**
> 🗓 활동 시기: 1940s–1991
> 🎹 주 악기: 트럼펫
> 🎼 장르/스타일: 모달 재즈 · 모달 재즈 (쿨·하드밥·퓨전 전반)
>
> Miles Davis는 쿨 재즈, 하드밥, 모달 재즈, 퓨전까지 재즈의 흐름이 바뀌는 순간마다 그 중심에 섰던 트럼페터입니다. 비브라토를 거의 쓰지 않는 담백한 톤과 음을 아끼는 여백의 미학으로, 화려한 속주보다 '무엇을 연주하지 않을지'를 고민한 연주자로 꼽힙니다. 1959년작 Kind of Blue는 복잡한 코드 진행 대신 몇 개의 스케일(모드) 위에서 즉흥연주하는 모달 재즈의 문을 열었습니다.
>
> 📖 **흥미로운 이야기**
> 1959년 Kind of Blue 녹음 날, 멤버들은 간단한 스케치만 받아 거의 리허설 없이 연주했고 대부분의 곡이 첫 테이크로 완성됐습니다. 이 앨범은 지금도 가장 많이 팔린 재즈 앨범 중 하나입니다.
> 🔗 [Wikipedia: Kind of Blue](https://en.wikipedia.org/wiki/Kind_of_Blue)
>
> 🎧 **대표곡**
> ① **So What**
> &nbsp;&nbsp;💿 Kind of Blue (1959)
> &nbsp;&nbsp;✨ 베이스의 물음에 혼 섹션이 'So what?' 하고 답하는 듯한 인트로 문답에 귀 기울여 보세요.
> &nbsp;&nbsp;▶ [YouTube Music에서 듣기](https://music.youtube.com/watch?v=VIDEO_ID_1)
>
> ② **Blue in Green**
> &nbsp;&nbsp;💿 Kind of Blue (1959)
> &nbsp;&nbsp;✨ Bill Evans의 몽환적인 피아노 위로 흐르는 약음기 트럼펫의 고요한 서정.
> &nbsp;&nbsp;▶ [YouTube Music에서 듣기](https://music.youtube.com/watch?v=VIDEO_ID_2)
>
> ③ **'Round Midnight**
> &nbsp;&nbsp;💿 'Round About Midnight (1957)
> &nbsp;&nbsp;✨ 하몬 뮤트의 쓸쓸한 테마 뒤, 짧은 팡파르와 함께 Coltrane의 테너가 이어받는 순간.
> &nbsp;&nbsp;▶ 링크 없음
>
> 🔰 **이 곡부터 들어보세요:** So What
> 단 두 개의 모드 위에서 진행돼 재즈가 처음이어도 흐름을 따라가기 쉽고, 트럼펫·색소폰·피아노 솔로마다 연주자의 개성이 또렷하게 들립니다.
>
> 📚 아티스트 위키백과: [English](https://en.wikipedia.org/wiki/Miles_Davis)
>
> `[ ▶ ① So What · YouTube Music에서 듣기 ]`
> `[ ▶ ② Blue in Green · YouTube Music에서 듣기 ]`
> `[ 📚 위키백과에서 더 알아보기 ]`

`/history` 응답 예:

> 📜 **최근 소개한 아티스트**
>
> • 10월 12일 (월) — **Miles Davis** (모달 재즈, 트럼펫)
> • 10월 11일 (일) — **Ella Fitzgerald** (스윙, 보컬)
> • 10월 10일 (토) — **Jaco Pastorius** (퓨전, 프렛리스 베이스)

---

## 🧩 다른 주제로 봇 만들기

같은 구조로 뉴스 봇 등을 만들려면 [`templates/daily-news-bot-prompt.md`](templates/daily-news-bot-prompt.md)의 프롬프트를 새 Claude Code 세션에 붙여 넣으세요.

---

## 🔐 보안 메모
- 모든 키는 `.env`(로컬)나 GitHub Secrets에서만 읽고, 코드에는 하드코딩하지 않습니다.
- 텔레그램 네트워크 오류 로그에는 토큰이 들어간 URL을 남기지 않습니다.
- ytmusicapi는 비공식 라이브러리라서 YouTube 쪽 변경으로 동작이 갑자기 바뀔 수 있습니다. 그래서 YouTube Data API를 대체 검색으로 두었습니다.
