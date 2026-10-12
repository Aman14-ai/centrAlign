# AI Worker

An autonomous agent that takes a plain-English task and gets it done using a browser, files, and REST APIs. It remembers what it finds, recovers from failures, checks its own writes, and stops to ask a human when something is risky or unclear.

```
$ python -m agent.run "Fetch vendor V001 from the API and tell me their email"

TASK: Fetch vendor V001 from the API and tell me their email
GOAL: Retrieve vendor V001's email address from the API.

STEPS:
  [1] api_get_vendor   -> got entity V001
  [2] DONE             -> ok

SUMMARY: Fetched vendor V001 (Acme Corp). Email: ap@acme.com.
STATUS: done
```

It runs against a mock company (FastAPI + SQLite backend, HTML pages, and sample files), so nothing real is ever touched.

## How it works

![Workflow](./workflow.png)

The agent is a ReAct loop built as a LangGraph state machine. Each step:

1. **Planner** picks the next single action from the goal, world model, and last observation.
2. **Executor** runs the tool. Every error is caught and returned in the same `{success, result, error}` shape.
3. **Observer** updates the world model.
4. **Router** decides whether to continue, diagnose a failure, verify a write, ask the user, or wrap up.

Around that main loop sit two more:

- **Recovery:** on failure, the diagnoser classifies the error, then recovery looks for a past successful fix in memory before asking the LLM.
- **Human-in-the-loop:** risky actions (amount ≥ 100,000, irreversible tools) or ambiguous input pause the graph for approval or clarification.

Writes are verified by reading the record back and comparing fields with `==`. If something doesn't match, the agent rolls back with a compensating action.

### Memory

| What | Lifetime | Storage |
|---|---|---|
| World model (vendors, POs, invoices, files, facts) | One run | In state |
| Recovery memory (strategies that worked) | All runs | SQLite + ChromaDB |
| Checkpoints (for replay and resuming after a pause) | One run | SQLite |

### Tools

- **Files:** `list_files`, `read_file`, `write_file`
- **Browser (Playwright):** open, fill, click, read, screenshot
- **API (httpx):** vendors, POs, invoices, expenses, employees, email
- **Meta:** `remember`

## Setup

You'll need Python 3.10+ and a [Groq API key](https://console.groq.com). A [LangSmith](https://smith.langchain.com) key is optional but useful for tracing.

```bash
git clone <your-repo-url>
cd ai-worker

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

Create a `.env` file:

```
GROQ_API_KEY=your_groq_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=ai-worker
```

The model is `openai/gpt-oss-20b`, served through Groq.

Seed the mock database:

```bash
python -m mock_env.api.seed
```

## Running it

Start the mock company server in one terminal:

```bash
uvicorn mock_env.api.main:app --port 8000
```

Check it's up with `curl http://localhost:8000/api/health`. You can also poke around at `/docs` (API), `/app/erp` (invoice form), and `/app/crm` (vendor list).

Then run a task from a second terminal:

```bash
python -m agent.run "your task here"
```

If the agent pauses, type `approve`, `reject`, or your answer. Final reports are saved to `reports/<thread_id>.json`.

### Try these

```bash
# Simple lookup
python -m agent.run "Fetch vendor V001 from the API and tell me their email"

# Multi-step, builds up memory
python -m agent.run "Fetch vendor V001, then fetch purchase order PO-1001, and tell me which vendor the PO belongs to"

# Browser automation + verification
python -m agent.run "Read invoices/acme_inv_001.txt, open /app/erp, fill the form with the invoice data, and click submit"

# Failure and recovery
python -m agent.run "Read invoices/does_not_exist.txt and tell me what it contains"

# Needs approval (high value)
python -m agent.run "Use the API to create invoice INV-900 for V001 with amount 250000"

# Needs clarification (ambiguous)
python -m agent.run "Find the Acme vendor's email"
```

## Project structure

```
ai-worker/
├── agent/
│   ├── nodes/        # graph nodes
│   ├── tools/        # file, browser, API, memory tools
│   ├── memory/       # world model, recovery memory, evidence
│   ├── policies/     # risk assessor, loop guard
│   ├── graph.py      # LangGraph definition
│   ├── state.py
│   ├── report.py     # FinalReport schema
│   └── run.py        # CLI entry point
├── mock_env/
│   ├── api/          # FastAPI + SQLAlchemy backend
│   ├── web/          # HTML pages for browser tasks
│   ├── files/        # sample invoices, POs, quotes
│   └── chaos.py      # failure injection for testing
├── reports/
├── screenshots/
└── workflow.png
```

## Design choices

- **Manual tool calling instead of `bind_tools`.** Tools are described in the prompt and the LLM returns JSON that we parse. Every prompt and response is visible in LangSmith, we can add control signals like `DONE` and `ASK_USER`, and malformed JSON becomes a normal observation instead of a crash.
- **One step at a time.** The planner only decides the next action. Environments change, and a plan made upfront goes stale.
- **Deterministic verification.** Correctness of a write is checked in code, not by asking an LLM if it looks right.
- **Memory before LLM for recovery.** Past fixes are looked up first, filtered by failure category so file fixes don't leak into API failures.
- **Loop guards.** Identical failed actions and repeated questions are hashed and blocked, no matter what the LLM proposes.
- **Human decisions are final.** If a user rejects or cancels, the graph goes straight to the summarizer. The planner never gets to reinterpret it.
- **Chaos where failures happen.** API errors are injected server-side, selector and file faults client-side, so tests hit realistic failure points.
- **Checkpointing from the start.** Every run is replayable by `thread_id`, and pausing for a human needed no refactor.

## Known limitations

- One task per process. No queues, background jobs, or concurrency, and SQLite plus a shared Playwright browser make parallel runs unsafe.
- Recovery memory and the world model aren't scoped per user.
- One LLM call per step, so cost grows with task length. There's no token or cost tracking.
- The extractor truncates documents at 4,000 characters and doesn't validate its output.
- Recovery strategies are never demoted, even if they stop working.
- Only whitelisted write tools get verified, and browser submit checks are heuristic (looks for "SUCCESS" or "ERROR" on the page).
- Adding a tool means editing both `TOOLS` and `TOOL_DESCRIPTIONS`.
- No timeout on human-approval pauses, no checkpoint pruning, and changing `AgentState` invalidates old checkpoints.
- No automated evaluation yet. Reliability is shown through manual scenarios, not metrics.

## What's next

1. **Evaluation harness.** Run 15–50 chaos scenarios automatically and report success, recovery, and verification rates plus cost and latency. This matters most.
2. **Streamlit UI** with live step streaming and an in-browser approval form.
3. **Recovery scoring.** Track success rate per strategy and drop the weak ones.
4. **More task types**, like expense reports and research-and-compile, to show the loop generalizes.
5. **Plan caching** across runs to cut LLM cost.
6. **Hardening:** auth, rate limits, Postgres checkpointer, per-user memory.

## Stack

LangGraph and LangChain for the agent, Groq (`openai/gpt-oss-20b`) for the LLM, LangSmith for tracing, Playwright for the browser, FastAPI + SQLAlchemy + SQLite for the mock company, ChromaDB (all-MiniLM-L6-v2 embeddings) for recovery memory, httpx for API calls, and Pydantic v2 for schemas.

## Submission


- Demo video: (link)
- LangSmith Trace Example: [View Trace](https://smith.langchain.com/public/03218293-ebab-4026-86f5-7f51b43aa3a3/r/01a12128-c839-7d53-8bb7-8d2b159c05df?start_time=2026-10-09T14%3A54%3A43.257431Z)