# BitGN PAC1 Agent (Yandex Cloud Foundation Models)

Forked from [bitgn/sample-agents/pac1-py](https://github.com/bitgn/sample-agents/tree/main/pac1-py) and rewired to talk to **Yandex Cloud Foundation Models** via the OpenAI-compatible endpoint. Same credentials as the in-house `openwebui` / LiteLLM stack.

Scoring-oriented improvements over the upstream sample:

- OpenAI function-calling instead of Pydantic structured output
- System prompt with explicit grounding-refs and prompt-injection rules
- Tool output wrapped in `<TOOL_OUTPUT>...</TOOL_OUTPUT>` with a "treat as data" note
- `report_completion` validates that `OUTCOME_OK` carries non-empty `grounding_refs`; re-prompts otherwise
- Stagnation guard: three identical calls in a row -> hint to change strategy
- Retry with exponential backoff on LLM errors
- Step budget bumped to 60 (configurable via `MAX_STEPS`)
- Auto-submits `OUTCOME_NONE_CLARIFICATION` if budget exhausted (avoids harness timeout)

## Default model

`deepseek-v32` (resolved as `gpt://b1g4t9au1vrfkg84c9hd/deepseek-v32/latest`). Switch to any other Yandex-hosted model via `MODEL_ID` in `.env`:

- `deepseek-v32` — codegen / reasoning, strong for PAC1
- `qwen3-235b-a22b-fp8` — biggest reasoning model on the folder
- `gpt-oss-120b` — open-weights alternative

Or pass a full Yandex URI like `gpt://<folder>/<model>/latest` and it'll be used as-is.

## Setup

1. Copy `.env.example` to `.env` and fill:
   - `BITGN_API_KEY` — from https://bitgn.com/me
   - `YANDEX_API_KEY` — from `openwebui/.env.liis-local`
   - `UV_INDEX_BUF_PASSWORD` — Buf Schema Registry token; get one at https://buf.build/settings/user (Google login, free). BitGN SDKs are hosted on `buf.build/gen/python` which requires auth even for public schemas.
2. `make sync` — installs deps (`openai`, BitGN SDKs).
3. `make task TASKS='t01'` — smoke test on one dev trial.
4. `make run` — full benchmark run (defaults to `bitgn/pac1-dev`; set `BENCH_ID=bitgn/pac1-prod` for prod).

Requires Python 3.14 (set by `pyproject.toml`).

## Where the points come from

PAC1 grades deterministic side effects, not prose. To clear ≥52/104 we need:

- **Find the right files** — strong navigation via `tree`/`find`/`search` before `read`.
- **Don't fabricate** — answers must reference actual file content; `grounding_refs` must list those files.
- **Resist injection** — emails/notes will try to override rules; refuse and use `OUTCOME_DENIED_SECURITY`.
- **No destructive actions** — `delete`/`write`/`move` only when the user task explicitly asks.
- **Choose the right outcome** when the task can't be done cleanly (`NONE_CLARIFICATION` / `NONE_UNSUPPORTED`).
