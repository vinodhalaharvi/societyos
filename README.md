# SocietyOS

> **Multi-agent collaboration framework** — configure a society of AI agents that negotiate, debate, and collectively solve complex tasks, powered by [Qwen](https://dashscope.aliyuncs.com/) (OpenAI-compatible API).

---

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Configuration](#configuration)
   - [Society Config (YAML)](#society-config-yaml)
   - [Environment Variables](#environment-variables)
6. [CLI](#cli)
7. [REST API & SSE Streaming](#rest-api--sse-streaming)
8. [Voting Strategies](#voting-strategies)
9. [Memory Types](#memory-types)
10. [Project Structure](#project-structure)
11. [Development](#development)
12. [Running Tests](#running-tests)

---

## Overview

SocietyOS lets you define a **society** of AI agents in a YAML file, assign each agent a distinct role, personality, weight, and memory type, then send a task to the whole group. Agents deliberate over multiple rounds, debate conflicting positions, vote on the best proposals, and collaborate on a final synthesised report.

Key properties:

- **Fully configurable** — everything (agents, rules, decision strategy, tools) lives in a single YAML file.
- **LLM-agnostic backbone** — defaults to Qwen (`qwen-plus`) via the OpenAI-compatible REST API; swap models with one env-var change.
- **Structured proposals** — every agent responds with a typed JSON object (`claim`, `confidence`, `reasoning`, `dependencies`), keeping outputs machine-readable.
- **Pluggable voting** — `weighted_vote`, `consensus`, `majority`, or `dictator`.
- **Persistent history** — every run, round, proposal, vote, and final report is stored in SQLite and queryable via the REST API.
- **SSE streaming** — the server streams live `RunEvent` objects over Server-Sent Events so UIs update in real time.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                         Coordinator                         │
│                                                             │
│  for round in 1..max_rounds:                               │
│    1. All agents think() in parallel  ──→  [Proposal, ...]  │
│    2. Conflict detection                                    │
│       └─ debate round for conflicting agents               │
│    3. Voting  ──→  winners written to Blackboard            │
│    4. Check for early consensus                             │
│                                                             │
│  Synthesizer agent reads full history  ──→  Final report    │
└─────────────────────────────────────────────────────────────┘
```

### Round lifecycle in detail

| Step | What happens |
|------|-------------|
| **think** | Every agent receives the task, the shared blackboard, and all prior proposals. It calls the LLM and returns a `Proposal`. |
| **conflict detection** | Proposals whose `confidence < CONFLICT_CONFIDENCE_THRESHOLD` (0.6) and that disagree with the majority are flagged as conflicts. |
| **debate** | Conflicting agents get a second LLM call with the instruction *"strengthen or revise your position with better evidence."* |
| **voting** | All proposals (original + debate) pass through the configured `VotingStrategy`. Winners are selected. |
| **blackboard** | Each winning proposal is written to the shared `Blackboard` under a key `round_{n}_{agent}`. |
| **consensus check** | If all winning proposals converge, the run ends early. |
| **synthesis** | A designated synthesiser agent writes the final human-readable report. |

---

## Architecture

```
societyos/
├── agents/
│   ├── base.py          # BaseAgent — calls LLM, builds messages, stores to memory
│   ├── factory.py       # AgentFactory — instantiates agents from SocietyConfig
│   ├── proposal.py      # Proposal dataclass — typed LLM output
│   ├── prompt.py        # compile_system_prompt — injects role, personality, rules
│   └── memory/
│       ├── base.py      # BaseMemory ABC
│       ├── none.py      # No-op memory
│       └── short_term.py# Fixed-size deque memory (default)
├── config/
│   ├── models.py        # Pydantic models: SocietyConfig, AgentConfig, …
│   └── loader.py        # load_config() — reads & validates YAML
├── society/
│   ├── coordinator.py   # Coordinator — orchestrates rounds, conflict, voting
│   ├── runner.py        # run_society() — wraps coordinator with DB persistence
│   ├── blackboard.py    # Blackboard — shared key-value store for agreed facts
│   ├── events.py        # RunEvent dataclass + SSE serialisation
│   └── voting/
│       ├── base.py      # BaseVotingStrategy ABC
│       ├── weighted.py  # WeightedVoteStrategy (default)
│       ├── consensus.py # ConsensusStrategy
│       ├── majority.py  # MajorityStrategy
│       └── factory.py   # build_voting_strategy()
├── db/
│   ├── connection.py    # aiosqlite connection pool
│   ├── migrations.py    # Schema creation on startup
│   └── queries/         # Typed async query functions per domain
│       ├── runs.py
│       ├── events.py
│       ├── votes.py
│       ├── reports.py
│       └── reputation.py
├── server/
│   ├── app.py           # FastAPI app, CORS, lifespan (migrations)
│   └── routes/runs.py   # /api/runs endpoints + SSE stream
├── cli.py               # Typer CLI (hello, validate, serve)
├── qwen_client.py       # Async wrapper around openai.AsyncOpenAI
└── settings.py          # Pydantic-settings — env vars with .env support
```

---

## Installation

### Prerequisites

- Python ≥ 3.10
- A Qwen API key from [Alibaba Cloud DashScope](https://dashscope.aliyuncs.com/) (or any OpenAI-compatible endpoint)

### Install

```bash
# clone the repo
git clone https://github.com/your-org/societyos.git
cd societyos

# create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# install in editable mode (includes CLI entry-point)
pip install -e .

# install dev extras (pytest, ruff, etc.)
pip install -e ".[dev]"
```

### Configure credentials

```bash
cp .env.example .env   # or create .env manually
```

Minimum `.env`:

```dotenv
QWEN_API_KEY=sk-...
```

---

## Configuration

### Society Config (YAML)

Societies are described in a YAML file. See `configs/examples/startup_board.yaml` for a full example.

```yaml
society:
  name: "Startup Board"
  decision_strategy: weighted_vote   # weighted_vote | consensus | majority | dictator
  max_rounds: 5                      # 1–20
  benchmark_vs_single_agent: true
  synthesizer: "Journalist"          # agent that writes the final report

agents:
  - name: CEO
    role: Strategic decision maker
    personality: visionary, bold, comfortable with risk, thinks long-term
    weight: 1.5          # 0.1–5.0, higher = more influence in weighted voting
    tools: [web_search]
    memory: short_term   # none | short_term | episodic

  - name: CFO
    role: Financial risk evaluator
    personality: conservative, data-driven, skeptical of projections
    weight: 1.2
    tools: [calculator]
    memory: short_term

  - name: Devil's Advocate
    role: Challenge every proposal to stress-test it
    personality: skeptical, contrarian, asks hard questions
    weight: 0.8
    tools: []
    memory: none

  - name: Journalist
    role: Synthesize all proposals into a clear final report
    personality: clear, concise, neutral, structured writer
    weight: 0.5
    tools: []
    memory: short_term

rules: |
  - Every claim must be backed by reasoning or data.
  - CFO has financial veto power.
  - Final report must include a Risk section and a Next Steps section.

tools:
  web_search:
    enabled: true
    options:
      provider: duckduckgo
  calculator:
    enabled: true

output:
  format: markdown        # markdown | json | html
  save_to: ./reports/
```

#### Top-level fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | — | Society identifier (stored in DB) |
| `decision_strategy` | enum | `weighted_vote` | How proposals are evaluated each round |
| `max_rounds` | int | `5` | Maximum deliberation rounds (1–20) |
| `benchmark_vs_single_agent` | bool | `true` | Whether to record benchmark metadata |
| `synthesizer` | string | last agent | Agent responsible for the final report |
| `rules` | string | `""` | Plain-text rules injected into every agent's system prompt |

#### Agent fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | — | Unique identifier |
| `role` | string | — | One-line role description (injected into system prompt) |
| `personality` | string | — | Character traits that shape the LLM's tone |
| `weight` | float | `1.0` | Voting influence multiplier (0.1–5.0) |
| `tools` | list[string] | `[]` | Tool names the agent may use |
| `memory` | enum | `short_term` | `none`, `short_term`, or `episodic` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QWEN_API_KEY` | *(required)* | API key for the LLM provider |
| `QWEN_BASE_URL` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | OpenAI-compatible endpoint |
| `QWEN_MODEL` | `qwen-plus` | Model name |
| `SOCIETYOS_DB_PATH` | `./societyos.db` | SQLite database file path |
| `SOCIETYOS_REPORTS_DIR` | `./reports` | Directory where markdown reports are saved |
| `SOCIETYOS_LOG_LEVEL` | `INFO` | Logging verbosity |
| `SOCIETYOS_CORS_ALLOW_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated CORS origins for the API server |

---

## CLI

```
societyos [COMMAND] [OPTIONS]
```

### `hello`

Smoke-test the installation.

```bash
societyos hello
# SocietyOS v0.1.0 — ready.
```

### `validate`

Load and validate a society config file, then print a summary table.

```bash
societyos validate configs/examples/startup_board.yaml
```

```
✓ Config valid: Startup Board

┌────────────────┬──────────────────────────┬────────────┬────────────┬────────┐
│ Name           │ Role                     │ Memory     │ Tools      │ Weight │
├────────────────┼──────────────────────────┼────────────┼────────────┼────────┤
│ CEO            │ Strategic decision maker │ short_term │ web_search │ 1.5    │
│ CFO            │ Financial risk evaluator │ short_term │ calculator │ 1.2    │
│ ...            │ ...                      │ ...        │ ...        │ ...    │
└────────────────┴──────────────────────────┴────────────┴────────────┴────────┘

Strategy: weighted_vote   Max rounds: 5   Benchmark: True
```

### `serve`

Start the FastAPI server.

```bash
societyos serve                        # defaults: 127.0.0.1:8000, reload=true
societyos serve --host 0.0.0.0 --port 9000 --no-reload
```

---

## REST API & SSE Streaming

The server is a standard FastAPI application. Interactive docs are available at `http://127.0.0.1:8000/docs`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check — returns `{"status":"ok","version":"..."}` |
| `POST` | `/api/runs` | Start a new run (SSE stream) |
| `GET` | `/api/runs` | List past runs (optional `?society_id=&limit=20`) |
| `GET` | `/api/runs/{run_id}` | Fetch a single run record |
| `GET` | `/api/runs/{run_id}/replay` | Replay all events (optional `?up_to_round=N`) |
| `GET` | `/api/runs/{run_id}/report` | Fetch the synthesised final report |

### Starting a run

`POST /api/runs` accepts JSON and returns a **Server-Sent Events** stream. Each line is a `data: {...}` JSON event.

```bash
curl -N -X POST http://127.0.0.1:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "config_path": "configs/examples/startup_board.yaml",
    "task": "Should we expand into the European market in Q3?"
  }'
```

### SSE Event types

| `event_type` | Description |
|--------------|-------------|
| `run_start` | Society and agent list |
| `round_start` | Beginning of a deliberation round |
| `proposal` | An agent's claim + confidence + reasoning |
| `conflict` | Conflicting proposals detected |
| `debate` | Rebuttal proposal from a conflicting agent |
| `vote` | Voting tally and winners |
| `blackboard_update` | A winning proposal written to the shared blackboard |
| `synthesis` | Final report content |
| `run_complete` | Run finished successfully |
| `error` | An exception was raised during the run |

---

## Voting Strategies

| Strategy | Behaviour |
|----------|-----------|
| `weighted_vote` | Scores each proposal as `confidence × agent_weight`. Winners are those scoring ≥ 50 % of the top score. |
| `consensus` | All agents must agree (confidence above threshold) for a proposal to pass. |
| `majority` | More than half of proposals must support a claim. |
| `dictator` | The agent with the highest weight always wins. |

Set the strategy per-society in the YAML under `decision_strategy`.

---

## Memory Types

| Type | Description |
|------|-------------|
| `none` | Agent starts each round with no prior context. |
| `short_term` | Fixed-size deque (default 20 items). The most recent proposals are appended to the agent's prompt. |
| `episodic` | *(planned)* Semantic retrieval from a long-term store. |

---

## Project Structure

```
societyos/                  # Main package
configs/examples/           # Example society YAML configs
tests/                      # pytest test suite
pyproject.toml              # Build config, dependencies, tool settings
.env                        # Local secrets (not committed)
societyos.db                # SQLite database (created on first run)
reports/                    # Saved markdown reports (created on first run)
```

---

## Development

```bash
# lint & auto-fix
ruff check . --fix

# format check
ruff format --check .

# run the server with live reload
societyos serve
```

### Adding a new voting strategy

1. Create `societyos/society/voting/my_strategy.py` implementing `BaseVotingStrategy.decide()`.
2. Register it in `societyos/society/voting/factory.py`.
3. Add the new key to the `decision_strategy` `Literal` in `societyos/config/models.py`.

### Adding a new memory type

1. Create `societyos/agents/memory/my_memory.py` extending `BaseMemory`.
2. Register it in `societyos/agents/memory/factory.py`.
3. Add the new key to the `memory` `Literal` in `societyos/config/models.py`.

---

## Running Tests

```bash
pytest                        # run all tests
pytest -v                     # verbose
pytest --cov=societyos        # with coverage report
```

Tests live in `tests/` and cover agents, config validation, health endpoint, orchestration, and DB persistence.

---

## License

MIT — see `LICENSE` for details.
