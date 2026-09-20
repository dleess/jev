# Jev (TypeSafe AI) API 키 2개 설치 — Claude Code + 터미널

Jev는 TypeSafe AI의 System One 모델. 텍스트를 생성하지 않고 choice / score / noul 형태의
판단값과 확률을 돌려준다. 키는 https://console.typesafe.ai/keys 에서 발급.

## 구성

| 키   | 용도                                   | 읽는 쪽                                  |
|------|----------------------------------------|------------------------------------------|
| KEY1 | 셸 환경변수 `TYPESAFE_API_KEY`         | Python/JS SDK, curl, 공식 TypeSafe 스킬  |
| KEY2 | Claude Code MCP 서버(jev-mcp) 전용     | `jev_classify` `jev_score` `jev_check` 도구 |

## 1. KEY1을 셸 환경변수로 등록

```bash
echo 'export TYPESAFE_API_KEY=<KEY1>' >> ~/.zshrc
source ~/.zshrc
```

## 2. KEY1 동작 확인 (curl)

```bash
curl -s -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state":"Please help ASAP, I am losing sales.","model":"jev-latest","questions":{"urgency":{"type":"noul","instructions":"Does this message express urgency?"}}}'
```

`"noul": 0.9x` 같은 확률값이 오면 성공.

## 3. Python SDK

Homebrew Python은 `pip3 install`을 막는다 (`externally-managed-environment`).
`--break-system-packages`는 쓰지 말고 `uv`를 쓴다.

일회성 확인:

```bash
uv run --with typesafe-sdk python -c "from typesafe_sdk import TypeSafeClient, Noul; print(TypeSafeClient().system_one(state='Help ASAP', questions={'u': Noul(instructions='Is this urgent?')}).answers['u'].noul)"
```

프로젝트에서 계속 쓸 때:

```bash
uv init && uv add typesafe-sdk
uv run python your_script.py
```

`python3 -c ...`로 직접 실행하면 `ModuleNotFoundError: No module named 'typesafe_sdk'` — 정상. 반드시 `uv run` 으로.

## 4. KEY2로 Claude Code MCP 서버 등록

```bash
claude mcp add --scope user jev -e TYPESAFE_API_KEY=<KEY2> -- npx -y jev-mcp
```

`-e`로 넘긴 값이 셸의 KEY1보다 우선하므로 MCP는 항상 KEY2를 쓴다. Node 20.12+ 필요.

## 5. MCP 확인

```bash
claude mcp list
```

`jev: npx -y jev-mcp - ✔ Connected` 가 보이면 완료. 첫 실행은 패키지 다운로드로 몇 초 걸린다.
Claude Code 재시작 후 "jev_models 도구로 키 확인해줘" 라고 하면 KEY2 유효성 검증.

## 6. (선택) 공식 TypeSafe 에이전트 스킬

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

## 미구현

두 키 자동 전환(pool). 한 키가 429를 자주 낼 때 추가.

## 참고

- https://docs.typesafe.ai/introduction/quickstart.md
- https://docs.typesafe.ai/agent-skill.md
- https://docs.typesafe.ai/sdk/python.md
- https://github.com/rashedInt32/jev-mcp
