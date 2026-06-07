# SocietyOS
# SocietyOS

**A configurable multi-agent platform where specialized AI citizens negotiate, debate, and collaborate to solve complex problems.**

Drop in a task. Watch a society of agents — each with a distinct role, memory, and voting weight — argue, revise, and synthesize a final report. Every decision is persisted and replayable via a visual time machine.

Built for the **Alibaba Cloud × Qwen Hackathon — Track 3: Agent Society**.

---

## Demo

![SocietyOS UI](docs/demo.gif)

```
societyos serve
# open http://localhost:8000
# click ▶ RUN SOCIETY
```

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/vinodhalaharvi/societyos.git
cd societyos

# 2. Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install
pip install -e ".[dev]"

# 4. Configure
cp .env.example .env
# Edit .env — add your QWEN_API_KEY

# 5. Run
societyos serve
# open http://localhost:8000
```

---

## What it does

| Feature | Description |
|---|---|
| **Configurable societies** | Define any agent society in a YAML file — roles, personalities, voting weights, tools, memory |
| **Rule engine** | Write rules in markdown — injected as the first block of every agent's system prompt |
| **Orchestration loop** | Decompose → assign → parallel execution → conflict detection → debate → vote → synthesize |
| **Pluggable voting** | `weighted_vote`, `majority`, `consensus`, `dictator` — set per society in config |
| **Persistent memory** | Every run, proposal, vote, and report saved to SQLite — nothing is lost |
| **Time machine** | Drag the timeline scrubber to replay any past run round by round |
| **Agent reputation** | Win/loss record tracked per agent per society across all runs |
| **D3 visualization** | Live force-directed graph — nodes pulse when thinking, edges flash when proposals travel |
| **Benchmark** | Every run compares society output vs a single-agent baseline |

---

## Society config

Define a society in YAML:

```yaml
society:
  name: "Startup Board"
  decision_strategy: weighted_vote   # weighted_vote | majority | consensus | dictator
  max_rounds: 5
  benchmark_vs_single_agent: true

agents:
  - name: CEO
    role: Strategic decision maker
    personality: visionary, bold, risk-tolerant
    weight: 1.5
    tools: [web_search]
    memory: short_term

  - name: CFO
    role: Financial risk evaluator
    personality: conservative, data-driven
    weight: 1.2
    tools: [calculator]
    memory: short_term

  - name: Devil's Advocate
    role: Challenge every proposal
    personality: skeptical, contrarian
    weight: 0.8
    tools: []
    memory: none

rules: |
  ## Board Rules
  - Every claim must be backed by reasoning or data.
  - CFO has financial veto on any unquantified cost proposal.
  - Final report must include a Risk section and Next Steps.

output:
  format: markdown
  save_to: ./reports/
```

Run it:

```bash
societyos validate configs/examples/startup_board.yaml
societyos serve
```

---

## Rule engine

Rules are written in markdown and compiled into the system prompt prefix for every agent:

```
You are {name}, the {role} in {society_name}.

## Society rules (follow these strictly)
- Every claim must be backed by reasoning or data.
- CFO has financial veto on any unquantified cost proposal.
...
```

The LLM reads rules before the task — they reliably shape agent behavior. Edit rules live in the UI rule editor and apply them to the next run.

---

## Architecture

```
Browser (index.html)
  │  POST /api/runs → SSE stream
  │  GET  /api/runs/{id}/replay?up_to_round=N  ← time machine
  ▼
FastAPI (uvicorn)
  │  Router → Runner → Coordinator → Agents (asyncio.gather)
  │                                      │
  │                                      └── chat() → Qwen Cloud API
  │                                               (qwen-plus model)
  │
  └── SQLite (WAL mode)
        runs · events · votes · reports · agent_reputation
```

See `architecture.png` for the full diagram.

---

## Project structure

```
societyos/
├── societyos/
│   ├── cli.py              # societyos hello | validate | serve
│   ├── settings.py         # env var config
│   ├── qwen_client.py      # async Qwen API wrapper
│   ├── config/
│   │   ├── models.py       # Pydantic: SocietyConfig, AgentConfig
│   │   └── loader.py       # YAML → validated SocietyConfig
│   ├── agents/
│   │   ├── base.py         # BaseAgent, RoundContext
│   │   ├── factory.py      # AgentFactory.build_all(config)
│   │   ├── proposal.py     # Proposal dataclass + JSON parser
│   │   ├── prompt.py       # System prompt compiler
│   │   └── memory/         # none | short_term | episodic
│   ├── society/
│   │   ├── coordinator.py  # Main orchestration loop
│   │   ├── blackboard.py   # Shared state between agents
│   │   ├── runner.py       # Coordinator + SQLite persistence
│   │   ├── events.py       # RunEvent → SSE
│   │   └── voting/         # weighted | majority | consensus
│   ├── db/
│   │   ├── migrations.py   # Schema creation on startup
│   │   ├── connection.py   # aiosqlite connection
│   │   └── queries/        # runs | events | votes | reports | reputation
│   └── server/
│       ├── app.py          # FastAPI app + static frontend
│       └── routes/runs.py  # REST + SSE endpoints
├── frontend/
│   └── index.html          # D3 graph + timeline + feed + rule editor
├── configs/examples/
│   └── startup_board.yaml
└── tests/                  # 66 passing tests
```

---

## CLI

```bash
societyos hello                                    # check install
societyos validate configs/examples/startup_board.yaml  # validate config
societyos serve                                    # start server at :8000
societyos serve --port 9000 --no-reload            # custom port
```

---

## API

```
POST /api/runs                    start a run (SSE stream)
GET  /api/runs                    list recent runs
GET  /api/runs/{id}               get run metadata
GET  /api/runs/{id}/replay        replay events (time machine)
  ?up_to_round=N                  filter to round N
GET  /api/runs/{id}/report        final report markdown
GET  /api/runs/{id}/reputation    agent win/loss record
GET  /health                      liveness check
```

---

## Tests

```bash
pytest tests/ -v   # 66 passing
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `QWEN_API_KEY` | — | Alibaba Cloud API key (required for real runs) |
| `QWEN_BASE_URL` | dashscope-intl endpoint | Qwen compatible API base URL |
| `QWEN_MODEL` | `qwen-plus` | Model name |
| `SOCIETYOS_DB_PATH` | `./societyos.db` | SQLite database file |
| `SOCIETYOS_REPORTS_DIR` | `./reports/` | Where reports are saved |

---

## Built with

- **Qwen Cloud** (Alibaba) — LLM for all agent reasoning
- **FastAPI** — async backend + SSE streaming
- **D3.js** — force-directed agent graph
- **SQLite** — WAL-mode persistence
- **Pydantic** — config validation
- **Python asyncio** — parallel agent execution

---

## License

MIT