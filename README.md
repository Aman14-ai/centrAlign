# AI Worker

An autonomous AI agent that takes a task in natural language and completes it using a browser, files, and APIs.

The main focus is not just task execution, but **handling failures and making safe decisions** when something goes wrong.

## What it does

Given a task like:

> "Read the latest invoice from Acme, enter it into the ERP, and verify it."

The agent:

* Understands the goal
* Chooses the next action
* Uses the required tool
* Observes the result
* Decides what to do next
* Handles failures instead of crashing
* Verifies the result
* Asks for clarification when it cannot safely continue

The agent does not directly access the database. Everything goes through its tools.

## Architecture

The agent is built as a **LangGraph ReAct loop**:

```text
             ┌─────────┐
             │ Intake  │
             └────┬────┘
                  ↓
             ┌─────────┐
             │ Planner │
             └────┬────┘
                  ↓
             ┌─────────┐
             │Executor │
             └────┬────┘
                  ↓
             ┌─────────┐
             │Observer │
             └────┬────┘
                  ↓
             ┌─────────┐
             │ Router  │
             └───┬─┬───┘
                 │ │
            continue summarize
                 │ │
                 └─┘
```

The planner only decides the **next action**, rather than creating the entire plan upfront. This allows the agent to react to what it actually observes.

### Core nodes

| Node         | Purpose                                |
| ------------ | -------------------------------------- |
| `intake`     | Converts the task into a clear goal    |
| `planner`    | Chooses the next action                |
| `executor`   | Runs the selected tool                 |
| `observer`   | Processes the result and updates state |
| `router`     | Decides whether to continue or finish  |
| `summarizer` | Produces the final result              |

## Tools

The executor uses a common tool interface:

```python
{
    "success": bool,
    "result": dict,
    "error": str | None
}
```

Available tools include:

**Files**

* `list_files`
* `read_file`

**Browser — Playwright**

* `browser_open`
* `browser_fill`
* `browser_click`
* `browser_read`
* `browser_screenshot`

**API — httpx**

* `api_get`
* `api_post`
* `api_get_invoice`
* `api_create_invoice`
* `api_get_vendor`
* `api_get_po`

Keeping the same result format makes it easier for the observer and planner to handle failures consistently.

## Mock Company Environment

The project includes a local company environment for testing the agent:

```text
mock_env/
├── api/              # FastAPI + SQLite
├── web/templates/    # ERP and CRM pages
├── files/            # Mock company documents
└── chaos.py          # Failure injection
```

It contains vendors, purchase orders, invoices and other company data.

Useful pages:

```text
http://localhost:8000/docs
http://localhost:8000/app/erp
http://localhost:8000/app/crm
```

`/docs` is the automatically generated FastAPI API documentation.

## Chaos Engineering

The mock environment can intentionally introduce failures so the agent can be tested against more than just the happy path.

Supported chaos:

| Setting             | Simulates                 |
| ------------------- | ------------------------- |
| `api_500_on`        | API failure               |
| `timeout_on`        | API timeout               |
| `selector_override` | Changed UI selector       |
| `missing_field`     | Missing document field    |
| `duplicate_invoice` | Duplicate invoice         |
| `ambiguous_vendor`  | Multiple matching vendors |

Example:

```bash
curl -X POST http://localhost:8000/api/chaos/set \
  -H "Content-Type: application/json" \
  -d '{"api_500_on": "/api/invoices"}'
```

Reset the environment:

```bash
curl -X POST http://localhost:8000/api/chaos/reset
```

The idea is to test whether the agent can **detect, adapt, retry, or ask for help** instead of blindly continuing.

## Setup

### Requirements

* Python 3.10+
* Groq API key
* LangSmith API key (optional)

### Install

```bash
git clone <your-repo-url>
cd ai-worker

python -m venv venv
venv\Scripts\activate       # Windows

pip install -r requirements.txt
playwright install chromium
```

Create `.env`:

```env
GROQ_API_KEY=your_groq_key

LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=ai-worker
```

Initialize the mock database:

```bash
python -m mock_env.api.seed
```

## Run

Start the mock company:

```bash
uvicorn mock_env.api.main:app --port 8000
```

Then, in another terminal:

```bash
python -m agent.run "Read invoices/acme_inv_001.txt, enter the invoice into the ERP, and verify it"
```

Some smaller tests:

```bash
python -m agent.run "List all files in the invoices folder"

python -m agent.run "Read invoices/acme_inv_001.txt and tell me the amount and vendor"

python -m agent.run "Open /app/erp and tell me the page title"

python -m agent.run "Fetch vendor V001 from the API and tell me their email"
```

## Project Structure

```text
ai-worker/
├── agent/
│   ├── graph.py
│   ├── state.py
│   ├── run.py
│   ├── llm.py
│   ├── nodes/
│   │   ├── intake.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── observer.py
│   │   ├── router.py
│   │   └── summarizer.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── files.py
│   │   ├── browser.py
│   │   └── api.py
│   └── memory/
│
├── mock_env/
│   ├── api/
│   ├── web/templates/
│   ├── files/
│   └── chaos.py
│
├── requirements.txt
├── .env.example
└── README.md
```

## Tech Stack

* **LangGraph** — agent state machine
* **Groq / Llama 3.3 70B** — LLM
* **Playwright** — browser automation
* **FastAPI** — mock company API
* **SQLAlchemy + SQLite** — database
* **Jinja2** — web pages
* **httpx** — API client
* **Pydantic** — validation
* **LangSmith** — tracing and debugging

## Current Status

The core agent loop, mock environment, browser/API/file tools, and LLM-based extraction are implemented.

The next focus is reliability:

* Better failure diagnosis and recovery
* Verification and rollback
* Human approval for risky actions
* Persistent memory
* Evaluation against injected chaos scenarios

## Notes

This is a local prototype. The mock company runs on `localhost:8000`, uses SQLite, and does not use real company credentials or data.
