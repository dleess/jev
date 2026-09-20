# Jev (TypeSafe AI) 설치 — Claude Code + 터미널

Jev는 TypeSafe AI의 System One 모델. 텍스트를 생성하지 않고 choice / score / noul 형태의
판단값과 확률을 돌려준다. 키는 https://console.typesafe.ai/keys 에서 발급.

## 최종 구성

```
터미널(curl/SDK) ──KEY1──┐
                          ├─▶ 키 pool 프록시 127.0.0.1:8790 ─▶ api.typesafe.ai
Claude Code(jev-mcp) ─KEY2┘      429 나면 keys 파일의 다음 키로 재시도
```

| 항목 | 값 |
|------|----|
| KEY1 | 셸 환경변수 `TYPESAFE_API_KEY` — curl, Python/JS SDK, 공식 TypeSafe 스킬 |
| KEY2 | Claude Code MCP 서버(jev-mcp) 전용 — `jev_check` `jev_classify` `jev_score` `jev_ask` `jev_triage` `jev_models` |
| 프록시 | `~/.config/typesafe/pool.py`, launchd `com.typesafe.pool` (KeepAlive) |
| 키 목록 | `~/.config/typesafe/keys` — 한 줄에 키 하나, 권한 600 |
| jev-mcp | `npm install -g jev-mcp` 전역 설치 (npx 아님) |

요구사항: Node 20.12+ (nvm 권장), `uv`, python3 3.9+.

## 1. 키 pool 프록시 설치

다른 모든 클라이언트가 이 프록시를 바라보므로 가장 먼저 설치한다. 저장소의 `pool/` 사용.

```bash
mkdir -p ~/.config/typesafe && chmod 700 ~/.config/typesafe
printf '<KEY1>\n<KEY2>\n' > ~/.config/typesafe/keys && chmod 600 ~/.config/typesafe/keys
cp pool/pool.py ~/.config/typesafe/
sed "s|~|$HOME|g; s|/opt/homebrew/bin/python3|$(which python3)|" pool/com.typesafe.pool.plist \
  > ~/Library/LaunchAgents/com.typesafe.pool.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.typesafe.pool.plist
```

확인:

```bash
launchctl print gui/$(id -u)/com.typesafe.pool | grep state   # state = running
lsof -nP -iTCP:8790 -sTCP:LISTEN                               # Python ... LISTEN
python3 ~/.config/typesafe/pool.py --selftest                  # selftest ok: A→429→B
```

동작: 클라이언트가 보낸 키를 먼저 쓰고, 429가 오면 keys 파일의 나머지 키를 순서대로 시도한다.
전환 기록은 `~/.config/typesafe/pool.log`. 키 파일은 기동 시 한 번만 읽는다.

## 2. 셸 환경변수 (KEY1 + 프록시 주소)

```bash
cat >> ~/.zshrc <<'ZRC'
# Jev (TypeSafe AI)
export TYPESAFE_API_KEY=<KEY1>
export TYPESAFE_BASE_URL=http://127.0.0.1:8790
ZRC
source ~/.zshrc
```

curl, Python SDK, JS SDK(jev-mcp) 모두 `TYPESAFE_BASE_URL`을 읽는다.

## 3. curl 확인

```bash
curl -s -X POST $TYPESAFE_BASE_URL/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state":"Please help ASAP, I am losing sales.","model":"jev-latest","questions":{"urgency":{"type":"noul","instructions":"Does this message express urgency?"}}}'
```

`"noul": 0.9x` 같은 확률값이 오면 프록시와 KEY1 모두 정상.

## 4. Python SDK

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

## 5. jev-mcp 전역 설치

```bash
npm install -g jev-mcp
which jev-mcp        # ~/.nvm/versions/node/<ver>/bin/jev-mcp
npm ls -g jev-mcp    # jev-mcp@0.5.x
```

npx 방식(`npx -y jev-mcp`)은 매 기동마다 패키지를 확인해 느리고 오프라인에서 실패한다.
전역 설치 후 절대 경로로 등록하면 GUI에서 띄운 Claude Code처럼 nvm PATH가 없는 환경에서도 동작한다.

## 6. KEY2로 Claude Code MCP 서버 등록

```bash
claude mcp remove --scope user jev 2>/dev/null   # 기존 npx 등록이 있으면 제거
claude mcp add --scope user jev \
  -e TYPESAFE_API_KEY=<KEY2> \
  -e TYPESAFE_BASE_URL=http://127.0.0.1:8790 \
  -- "$(which jev-mcp)"
```

`-e`로 넘긴 값이 셸의 KEY1보다 우선하므로 MCP는 항상 KEY2를 먼저 쓴다.
결과는 `~/.claude.json`의 `mcpServers.jev`에 저장된다:

```json
"jev": {
  "type": "stdio",
  "command": "/Users/<user>/.nvm/versions/node/v24.14.1/bin/jev-mcp",
  "args": [],
  "env": { "TYPESAFE_API_KEY": "<KEY2>", "TYPESAFE_BASE_URL": "http://127.0.0.1:8790" }
}
```

## 7. MCP 확인

```bash
claude mcp list
```

`jev: /Users/<user>/.nvm/.../jev-mcp - ✔ Connected` 가 보이면 완료.
Claude Code를 재시작한 뒤 "jev_check로 'The sky is blue'가 하늘 얘기인지 확인해줘" 라고 하면
`probability_yes: 0.99`, `model: jev-1.13.0` 같은 응답으로 KEY2와 프록시 경로를 검증할 수 있다.

## 8. (선택) 공식 TypeSafe 에이전트 스킬

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

## 9. 운영

| 상황 | 조치 |
|------|------|
| 키 추가/교체 | `~/.config/typesafe/keys`에 한 줄 추가 후 `launchctl kickstart -k gui/$(id -u)/com.typesafe.pool` |
| 키 상태 점검 | keys 파일의 각 키로 3번의 curl을 `https://api.typesafe.ai`에 직접 보내 200/429 확인 |
| 프록시가 죽음 | SDK/MCP 호출이 모두 실패. `unset TYPESAFE_BASE_URL` 로 직접 호출하거나 `launchctl kickstart` |
| Node 버전 변경 | 새 버전에서 `npm install -g jev-mcp` 후 6번을 다시 실행해 경로 갱신 |
| jev-mcp 업데이트 | `npm update -g jev-mcp` 후 Claude Code 재시작 |
| pool.py 수정 | `cp pool/pool.py ~/.config/typesafe/` 후 `launchctl kickstart -k gui/$(id -u)/com.typesafe.pool` |

`~/.claude.json`에는 KEY2가 평문으로 들어간다. 백업·공유 시 주의.

## 참고

- https://docs.typesafe.ai/introduction/quickstart.md
- https://docs.typesafe.ai/agent-skill.md
- https://docs.typesafe.ai/sdk/python.md
- https://github.com/rashedInt32/jev-mcp
