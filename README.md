
# Text-to-SQL Agent

A natural language to SQL pipeline that lets you query a PostgreSQL database using plain English. Built with FastAPI, LangChain, LangGraph, and Groq.

## What It Does

You type a question like:

> "How many customers are from the USA?"

The system returns:

```json
{
  "sql": "SELECT COUNT(*) FROM customers WHERE country = 'USA'",
  "result": [{"count": 36}],
  "summary": "The answer to your question is: 36",
  "status": "success"
}
```

## How It Works

The pipeline has five steps:

1. **Decompose** — breaks the question into intent, tables, columns, filters and joins
2. **Generate** — converts the decomposition into a SQL query
3. **Validate** — blocks any non-SELECT queries before they reach the database
4. **Execute** — runs the SQL against PostgreSQL
5. **Fix and Retry** — if execution fails, reads the error and attempts to fix the SQL (up to 3 retries)

## Project Structure
```
## Project Structure

TEXT2SQLAGENT/
│
├── data/
│   ├── decompositions.csv
│   ├── seed.sql
│   └── sql_questions_only.csv
│
├── logs/
│   ├── evaluation_report.json
│   ├── evaluation_summary.txt
│   ├── evaluation_table.csv
│   └── query_logs.json
│
├── src/
│   ├── api/
│   │   └── main.py
│   │
│   ├── core/
│   │   ├── decomposition.py
│   │   └── sql_generator.py
│   │
│   ├── database/
│   │   └── database.py
│   │
│   ├── engine/
│   │   ├── evaluate.py
│   │   ├── executor.py
│   │   └── validator.py
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── templates.py
│   │
│   └── ui/
│       └── streamlit_app.py
│
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── README.md
└── requirements.txt

```


## Tech Stack

| Component | Technology |
|---|---|
| API | FastAPI |
| LLM | Groq (Llama 3.3 70B) |
| LLM Framework | LangChain |
| Agent Framework | LangGraph |
| Database | PostgreSQL |
| UI | Streamlit |
| Container | Docker |

## Setup

**1. Clone the repository**
```bash
git clone <your-repo-url>
cd Text2SQLAgent
```

**2. Create your `.env` file**
```bash
cp .env.example .env
```

Fill in your credentials:
```
DB_HOST=db
DB_PORT=5432
DB_NAME=classicmodels
DB_USER=your_db_user
DB_PASSWORD=your_db_password
GROQ_API_KEY=your_groq_api_key
```

**3. Start the services**
```bash
docker-compose up --build
```

This starts three services:
- PostgreSQL on port 5433 (seeded automatically with classicmodels data)
- FastAPI on port 8001
- Streamlit on port 8501

## Usage

### Streamlit Chat UI
Open your browser and go to:
```
http://localhost:8501
```
Type any question about the database in plain English.

### FastAPI Docs
```
http://localhost:8001/docs
```
Use the interactive docs to test the API directly.

### API Request
```bash
curl -X POST http://localhost:8001/agent/sql \
  -H "Content-Type: application/json" \
  -d '{"question": "How many customers are from the USA?"}'
```

---

## Running the Evaluation

To run all benchmark questions through the pipeline:
```bash
docker-compose exec app python evaluate.py
```

Results are saved to:
- `logs/evaluation_report.json` — detailed per-question results
- `logs/evaluation_summary.txt` — overall metrics summary

---

## Running Query Decomposition

To generate structured decompositions for all benchmark questions:
```bash
docker-compose exec app python decomposition.py
```

Results are saved to `data/decompositions.csv`.

## Database

The system uses the **ClassicModels** dataset — a sample database representing a scale model car retailer with the following tables:

| Table | Description |
|---|---|
| customers | Customer information and contacts |
| orders | Customer orders and status |
| orderdetails | Line items for each order |
| products | Product catalog with pricing |
| productlines | Product categories |
| employees | Staff and reporting structure |
| offices | Office locations |
| payments | Customer payment records |


## Example Questions

```
How many customers are from the USA?
Show all orders placed by customers in Germany
What is the total revenue from payments?
List employees and their managers
Which product line has the highest average price?
Show total payments per customer
```

## Logs

Every query execution is logged to `logs/query_logs.json` with:
- Timestamp
- Original question
- Generated SQL
- Execution status
- Number of retries
- Total time taken
- Error message if failed

## Notes

- Only SELECT queries are allowed. DELETE, DROP, UPDATE and INSERT are blocked.
- Maximum 3 retry attempts per query.
- All query executions are logged automatically.
- The database is seeded automatically on first Docker startup.
```
