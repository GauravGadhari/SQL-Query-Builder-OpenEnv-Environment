# 🧠 SQL Query Builder — OpenEnv Environment

> **Train AI agents to write SQL queries against a realistic company database.**
> Built for the [Meta PyTorch OpenEnv Hackathon 2026](https://openenv.ai) · Team Rocket 🚀

---

## 🌟 What is this?

The SQL Query Builder is a **real-world** OpenEnv environment where AI agents learn to translate natural-language questions into correct SQL queries. It simulates what millions of data analysts do daily — querying relational databases.

**Key Features**:
- 📊 **Realistic database**: 5 departments, 20 employees, 30 sales records with proper foreign keys
- 🎯 **21 unique questions** across 3 difficulty tiers (easy → medium → hard)
- ⚖️ **5-signal partial reward** — agents get meaningful feedback at every step, not just pass/fail
- 🔄 **Self-correction loop** — agents get 3 attempts with detailed feedback to fix their queries
- 🧹 **Clean isolation** — fresh SQLite database on every `reset()` call

---

## 🏗️ Architecture

```
sql_query_env/
├── inference.py          # Baseline inference script (runs agent against env)
├── models.py             # Pydantic Action & Observation models
├── client.py             # WebSocket client wrapper
├── openenv.yaml          # OpenEnv manifest
├── pyproject.toml        # Dependencies & metadata
├── README.md             # You are here
└── server/
    ├── app.py            # FastAPI server (step/reset/state endpoints)
    ├── sql_query_env_environment.py  # Core environment logic
    ├── database.py       # SQLite schema & seed data
    ├── grader.py         # 5-signal SQL grader
    ├── tasks.py          # 21 task definitions with expected SQL
    └── Dockerfile        # Production container
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [openenv-core](https://pypi.org/project/openenv-core/): `pip install openenv-core`
- An LLM API key (HuggingFace, NVIDIA, OpenAI, etc.)

### 1. Install Dependencies

```bash
cd sql_query_env
pip install -e ".[inference]"
```

### 2. Start the Server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Run Inference

In a separate terminal:

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your-api-key-here"

PYTHONPATH=".." python inference.py
```

### 4. Docker (Production)

```bash
# Build
DOCKER_BUILDKIT=1 docker build -t sql-query-env -f server/Dockerfile .

# Run
docker run -p 8000:8000 sql-query-env

# Test health
curl http://localhost:8000/health
# → {"status":"healthy"}
```

---

## 📋 Tasks & Difficulty

Each task picks a random question from its pool on every `reset()`.

| Task | Difficulty | Questions | SQL Concepts |
|------|:---------:|:---------:|-------------|
| `simple_lookup` | 🟢 Easy | 7 | `SELECT`, `WHERE`, `JOIN`, `ORDER BY`, `IN` |
| `analytics_query` | 🟡 Medium | 7 | `GROUP BY`, `HAVING`, subqueries, aggregates, `COUNT`/`AVG` |
| `complex_report` | 🔴 Hard | 7 | Window functions (`RANK`, `SUM OVER`), CTEs, running totals |

### Example Questions

| Tier | Example |
|------|---------|
| 🟢 Easy | *"Find the employee with email 'alice@company.com'. Return her name and role."* |
| 🟡 Medium | *"Find the top 3 departments by average salary. Return dept name, avg_salary, num_employees."* |
| 🔴 Hard | *"Calculate a running cumulative sales total for each salesperson over time."* |

---

## ⚖️ Reward Function

The grader evaluates queries using **5 independent signals** with partial credit:

| Signal | Weight | What it checks |
|--------|:------:|---------------|
| `syntax_valid` | 10% | Does the SQL parse correctly? |
| `executes` | 15% | Does it run without runtime errors? |
| `correct_columns` | 15% | Are the output column names correct? |
| `correct_rows` | 25% | Is the row count correct? |
| `values_match` | 35% | Do the actual data values match? |

**Total reward** = weighted sum, capped at `[0.0, 1.0]`.

> 💡 This means an agent that writes syntactically valid SQL that runs but returns wrong data still gets **0.25** — providing learning signal even for poor attempts.

---

## 🔄 Action & Observation Spaces

### Action (`SqlQueryAction`)

```python
class SqlQueryAction(Action):
    query: str  # SQL query string to execute
```

### Observation (`SqlQueryObservation`)

| Field | Type | Description |
|-------|------|------------|
| `db_schema` | `str` | Database schema as CREATE TABLE statements |
| `question` | `str` | Natural-language question to answer |
| `task_name` | `str` | `simple_lookup` · `analytics_query` · `complex_report` |
| `task_difficulty` | `str` | `easy` · `medium` · `hard` |
| `hints` | `list[str]` | Optional hints for the agent |
| `agent_result` | `list[dict]` | Rows returned by agent's query |
| `expected_result` | `list[dict]` | Expected result (revealed after episode ends) |
| `feedback` | `str` | Actionable grading feedback |
| `reward_breakdown` | `dict` | Per-signal reward scores |
| `error` | `str \| None` | SQL error message (if query failed) |
| `attempts_remaining` | `int` | Remaining attempts (starts at 3) |
| `done` | `bool` | Whether the episode is complete |
| `reward` | `float` | Reward score `0.0` – `1.0` |

---

## 🗄️ Database Schema

```sql
TABLE: departments
  - id          INTEGER  PRIMARY KEY
  - name        TEXT     department name
  - budget      REAL     annual budget (USD)
  - location    TEXT     office location

TABLE: employees
  - id              INTEGER  PRIMARY KEY
  - name            TEXT     full name
  - email           TEXT     email address
  - department_id   INTEGER  → departments.id
  - salary          REAL     annual salary (USD)
  - hire_date       TEXT     YYYY-MM-DD
  - role            TEXT     job title

TABLE: sales
  - id              INTEGER  PRIMARY KEY
  - employee_id     INTEGER  → employees.id
  - amount          REAL     sale amount (USD)
  - product         TEXT     Widget A / B / C
  - sale_date       TEXT     YYYY-MM-DD
  - region          TEXT     North / South / East / West
```

**5 departments** · **20 employees** · **30 sales records** · Fresh DB on every `reset()`

---

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|----------|:--------:|---------|------------|
| `API_BASE_URL` | ✅ | `https://router.huggingface.co/v1` | LLM API endpoint |
| `MODEL_NAME` | ✅ | `Qwen/Qwen2.5-72B-Instruct` | Model identifier |
| `HF_TOKEN` | ✅ | — | API key (also accepts `API_KEY`) |
| `ENV_URL` | ❌ | `http://localhost:8000` | Environment server URL |
| `IMAGE_NAME` | ❌ | — | Docker image name (for `from_docker_image()`) |

---

## 📊 Baseline Scores

Tested with `nvidia/nemotron-3-super-120b-a12b`:

| Task | Score | Steps | Time |
|------|:-----:|:-----:|:----:|
| 🟢 `simple_lookup` | **1.00** | 1 | ~2s |
| 🟡 `analytics_query` | **1.00** | 1-2 | ~10s |
| 🔴 `complex_report` | **1.00** | 1-2 | ~12s |

> All 3 tasks achieve perfect scores with self-correction within 3 attempts.

---

## 🧪 Use as Client (Python)

```python
from sql_query_env import SqlQueryAction, SqlQueryEnv

async with SqlQueryEnv(base_url="http://localhost:8000") as env:
    # Reset with a specific task
    result = await env.reset(options={"task": "simple_lookup"})
    obs = result.observation
    
    print(f"Question: {obs.question}")
    print(f"Schema: {obs.db_schema}")

    # Submit a query
    result = await env.step(SqlQueryAction(
        query="SELECT name, role FROM employees WHERE email = 'alice@company.com'"
    ))
    
    print(f"Score: {result.reward}")              # 0.0 - 1.0
    print(f"Feedback: {result.observation.feedback}")
    print(f"Done: {result.done}")
```

---

## 🏆 Team Rocket

**Meta PyTorch OpenEnv Hackathon 2026**

| Member | Role |
|--------|------|
| **Gaurav Gadhari** | Team Lead |
| **Gaurav Khokle** | Developer |
| **Aryan Prakash Bargat** | Developer |

---

## 📜 License

BSD-3-Clause · Meta Platforms, Inc.
