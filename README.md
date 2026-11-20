# 🤖 Data Agent

A multi-agent data assistant built with **LangGraph** and **LangChain**. Ask a question in plain language (English or Roman Urdu) and the agent decides whether to **query a PostgreSQL database** or **run an ETL job**, then replies with a clear answer.

## What the Analysts Do

### 🗄️ SQL Analyst

**The problem it solves:** Business owners and managers often want quick answers from their data, like *"How much sales did we make this month?"* or *"Which driver completed the most rides?"*, sometimes late at night when no analyst or data engineer is available. Most of them don't know SQL, and waiting for someone to write a query wastes time.

**How it helps:** The owner just types the question in simple English or Roman Urdu. The SQL Analyst:
1. Rewrites the question to be clear and specific.
2. Reads the database schema and generates the right PostgreSQL query.
3. Checks the query with a safety judge that blocks anything that could modify data (`INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.), so the data stays protected.
4. Runs the query and explains the result in simple language, with no technical jargon.

No SQL knowledge, no waiting, and no risk of accidentally changing the data.

### 🔄 ETL Analyst

**The problem it solves:** Getting data from an API, cleaning it and reshaping it normally needs someone who can write code. This makes that work possible with a simple instruction.

**What it does:** It uses two tools:
- **Extract & Load**: pulls data from an API endpoint and saves it as `csv`, `json` or `parquet`.
- **Transform & Load**: takes a saved file, writes Pandas code based on your instruction (e.g. "keep only bulbasaur"), runs it, and saves the transformed data.

## Memory

Conversation state is saved in PostgreSQL per `thread_id`.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
DB_URI=postgresql://user:password@localhost:5432/your_db
GROQ_API_KEY=your_groq_key
DEEPSEEK_API_KEY=your_deepseek_key
```

Load the sample ride-sharing data (this truncates the tables first):

```bash
python feed_db.py
```

## Usage

```bash
python -m agents.data_agent
```

Example: *"Tell me Top 5 customers by total sales"*

## Safety Notes

- Use a **read-only DB user** in production, since the SQL judge is only an LLM check.
- The ETL Analyst uses `exec()` on LLM-generated code, so run it only in a trusted environment.