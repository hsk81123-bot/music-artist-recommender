#!/usr/bin/env bash
# 내 PC에서 Daily Jazz를 보낸다. cron(또는 작업 스케줄러)이 정기적으로 호출한다.
#
# - 오늘 이미 보냈으면 daily.py가 바로 끝나므로 여러 번 호출해도 중복 발송되지 않는다.
# - PC가 꺼져 있었다면 켜진 뒤 다음 호출 때 놓친 발송을 한 번 채운다.
# - 발송 기록(data/history.json)은 커밋해서 GitHub에 올린다. /today, /history 명령이 이 기록을 쓰기 때문이다.
set -u

# cron에는 입력할 사람이 없으므로 git이 로그인 정보를 묻지 않고 바로 실패하게 한다.
# 인증 정보는 미리 한 번 터미널에서 git pull 하면서 키체인에 저장해 둔다(README 7번).
export GIT_TERMINAL_PROMPT=0

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
mkdir -p logs
exec >>logs/daily.log 2>&1
echo "=== $(date '+%F %T') 시작"

# 사용할 Python 찾기: ① JAZZBOT_PYTHON(환경변수 또는 .env) ② conda 환경 "jazzbot" ③ .venv ④ python3
# cron은 conda 환경을 활성화하지 않으므로 환경 안의 python 경로를 직접 쓴다.
PY="${JAZZBOT_PYTHON:-}"
if [ -z "$PY" ] && [ -f .env ]; then
  PY="$(grep -E '^JAZZBOT_PYTHON=' .env | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
fi
PY="${PY/#\~/$HOME}"
if [ -z "$PY" ]; then
  for base in "$HOME/miniconda3" "$HOME/miniforge3" "$HOME/anaconda3" "$HOME/opt/miniconda3" \
              "/opt/homebrew/Caskroom/miniconda/base" "/opt/miniconda3"; do
    if [ -x "$base/envs/jazzbot/bin/python" ]; then PY="$base/envs/jazzbot/bin/python"; break; fi
  done
fi
if [ -z "$PY" ]; then
  if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
  elif [ -x .venv/Scripts/python.exe ]; then
    PY=.venv/Scripts/python.exe
  else
    PY=python3
  fi
fi
if ! [ -x "$PY" ] && ! command -v "$PY" >/dev/null 2>&1; then
  echo "오류: Python을 찾을 수 없습니다: $PY"
  exit 1
fi
echo "Python: $PY"

git pull --rebase -q origin main || echo "경고: git pull 실패(오프라인이거나 GitHub 인증이 저장되지 않음). 현재 코드로 진행합니다."

"$PY" -m jazzbot.daily
status=$?

if [ -n "$(git status --porcelain data/)" ]; then
  git add -A data/
  git commit -q -m "chore: daily jazz history $(TZ=Asia/Seoul date +%F) (local)"
fi

# 이번에 만든 커밋뿐 아니라, 이전 실행에서 올리지 못한 커밋도 함께 올린다.
ahead="$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"
if [ "$ahead" -gt 0 ]; then
  pushed=0
  for i in 1 2 3; do
    if git pull --rebase -q origin main && git push -q origin HEAD:main; then
      pushed=1
      break
    fi
    sleep $((i * 5))
  done
  [ "$pushed" = 1 ] || echo "오류: 발송 기록을 GitHub에 올리지 못했습니다(커밋 ${ahead}개 대기). GitHub 인증을 확인하세요. 다음 실행 때 다시 시도합니다."
fi

echo "=== $(date '+%F %T') 종료 (코드 $status)"
exit "$status"
