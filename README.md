# 🤖 NL2SQL Agent

An AI-powered agentic system that converts plain English business questions into safe, optimized SQL queries — with a full Streamlit UI, FastAPI backend, and PostgreSQL demo database.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.39-red?logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

- **2-stage AI pipeline** — intent extraction → SQL generation with chain-of-thought reasoning
- **Self-correction loop** — automatically retries up to 2 times if SQL fails to execute
- **Clarification agent** — asks for clarification when the question is ambiguous
- **Security layer** — SELECT-only enforcement, dangerous keyword blocklist, auto LIMIT injection
- **Live schema introspection** — agent always reads the real DB schema at query time
- **Evaluation framework** — tracks latency, token usage, self-corrections, and error rate per query
- **Human feedback** — rate any query result via API or UI
- **Demo e-commerce DB** — auto-seeded with 50 customers, 20 products, 200 orders

---

## 🏗️ Architecture

```
User Question
      │
      ▼
┌─────────────────────────────────────┐
│     Stage 1: IntentExtraction       │
│                                     │
│  LLaMA 3.3 70B extracts:            │
│  • intent_type (aggregation/join/…) │
│  • entities  (tables/columns)       │
│  • time_range                       │
│  • ambiguity_flags                  │
│                                     │
│  ambiguity_flags non-empty?         │
│  → return ClarificationRequest      │
└──────────────┬──────────────────────┘
               │ QueryIntent
               ▼
┌─────────────────────────────────────┐
│     Stage 2: SQLGeneration          │
│                                     │
│  1. Fetch live DB schema            │
│  2. LLaMA reasons step-by-step:     │
│     Step 1 – identify tables        │
│     Step 2 – determine joins        │
│     Step 3 – write SQL              │
│     Step 4 – self-review            │
│  3. Security validation             │
│  4. Execute SQL                     │
│  5. Self-correction loop (≤ 2×)     │
└──────────────┬──────────────────────┘
               │ GeneratedSQL + Results
               ▼
         QueryResponse
  sql · explanation · results
  latency · tokens · cost · corrections
```

---

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A **free** Groq API key → [console.groq.com](https://console.groq.com/) *(no credit card required)*

### 1. Clone & configure

```bash
git clone https://github.com/jenish0908/nl2sql.git
cd nl2sql
cp .env.example .env
```

Open `.env` and set your key:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

### 2. Launch

```bash
docker-compose up --build
```

On first boot the app will:
1. Create all database tables
2. Seed the demo e-commerce dataset
3. Start the FastAPI backend
4. Start the Streamlit UI

| Service | URL |
|---|---|
| 🖥️ Streamlit UI | http://localhost:8501 |
| ⚡ FastAPI docs | http://localhost:8001/docs |
| 🗄️ PostgreSQL | localhost:5433 |

---

## 💬 Example Questions

```
Which category had the highest revenue last month?
Show me the top 5 customers by total order value
Which products are running low on stock?
What is the average order value by city?
How many orders were placed last week by status?
Which supplier has the best-rated products?
Show total revenue per month for the last 3 months
What is the profit margin per product category?
Which customers placed more than 3 orders?
Show me cancelled orders from the last 30 days
```

---

## 📡 API Reference

### `POST /query`
```json
{
  "question": "Which city had the highest order value last month?"
}
```

Response:
```json
{
  "query_id": 1,
  "sql": "SELECT delivery_city, SUM(total_amount) AS total ...",
  "explanation": "This query groups orders by delivery city ...",
  "results": [{"delivery_city": "New York", "total": 14230.50}],
  "row_count": 5,
  "intent": {"intent_type": "aggregation", "time_range": "last month"},
  "latency_ms": 1240,
  "tokens_used": 980,
  "cost_usd": 0.0,
  "self_corrections": 0
}
```

### `POST /query/clarify`
Re-run with extra context when the agent asks for clarification.
```json
{
  "question": "Show me sales",
  "clarification": "I mean total revenue by product category for last month"
}
```

### `GET /schema`
Returns the full live database schema (tables, columns, types, foreign keys).

### `GET /history`
Returns the last 20 queries with SQL, results summary, and metrics.

### `GET /evaluations/summary`
```json
{
  "total_queries": 47,
  "avg_latency_ms": 1340,
  "avg_cost_usd": 0.0,
  "self_correction_rate": 0.04,
  "clarification_rate": 0.06,
  "error_rate": 0.02
}
```

### `POST /evaluations/{query_id}/feedback`
```json
{
  "sql_correct": true,
  "result_correct": true,
  "rating": 5,
  "comment": "perfect"
}
```

### `GET /health`

---

## 🔒 Security

| Layer | Detail |
|---|---|
| SELECT-only | Non-SELECT statements are rejected immediately |
| Keyword blocklist | `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `EXEC`, `TRUNCATE`, `XP_`, `SP_` |
| Comment stripping | `--` and `/* */` comments removed before validation |
| Auto LIMIT | `LIMIT 100` appended if no LIMIT clause present |
| Parameterized execution | All queries run through SQLAlchemy's safe layer |

---

## 📊 Evaluation Metrics

Every query automatically records:

| Metric | Description |
|---|---|
| `latency_ms` | Total wall-clock time from question to response |
| `tokens_used` | Combined input + output tokens across both agent stages |
| `cost_usd` | $0 on Groq free tier |
| `self_corrections` | SQL retry count (0–2) |
| `clarification_requested` | Whether the intent stage flagged ambiguity |
| `execution_error` | Whether all retries were exhausted |

---

## 🗂️ Project Structure

```
nl2sql-agent/
├── app/
│   ├── main.py                   FastAPI app + lifespan
│   ├── config.py                 Settings (pydantic-settings)
│   ├── agents/
│   │   ├── intent_extraction.py  Stage 1 – Groq intent parsing
│   │   ├── sql_generation.py     Stage 2 – Groq SQL + self-correction
│   │   └── clarification.py      Clarification subagent
│   ├── api/
│   │   ├── query.py              POST /query, POST /query/clarify
│   │   ├── schema.py             GET /schema
│   │   └── evaluations.py        GET /history, /evaluations/summary, feedback
│   ├── services/
│   │   ├── db.py                 Async SQLAlchemy engine + session
│   │   ├── schema_inspector.py   Live schema introspection
│   │   └── sql_executor.py       Safe SQL execution + security checks
│   └── models/
│       ├── database.py           SQLAlchemy ORM models
│       └── schemas.py            Pydantic v2 request/response schemas
├── streamlit_app.py              Streamlit demo UI
├── scripts/
│   └── seed_demo_data.py         Demo e-commerce data seeder
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh
├── requirements.txt
└── .env.example
```

---

## 🛠️ Local Development (without Docker)

```bash
# Start only Postgres via Docker
docker run -d \
  -e POSTGRES_USER=nl2sql \
  -e POSTGRES_PASSWORD=nl2sql \
  -e POSTGRES_DB=nl2sql_db \
  -p 5432:5432 \
  postgres:15-alpine

# Install dependencies
pip install -r requirements.txt

# Configure env (use localhost URLs)
cp .env.example .env

# Create tables + seed data
python scripts/seed_demo_data.py

# Start API
uvicorn app.main:app --reload

# Start UI (separate terminal)
streamlit run streamlit_app.py
```

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| LLM | Groq — LLaMA 3.3 70B Versatile (free) |
| Backend | FastAPI + Uvicorn |
| Database | PostgreSQL 15 + SQLAlchemy (async) |
| UI | Streamlit |
| Validation | Pydantic v2 |
| Infra | Docker + Docker Compose |

---

## 📄 License

MIT
