"""AI business Q&A: question -> LLM writes SQL -> validated, read-only execution -> LLM explains the rows."""
import datetime as dt, json, os, re
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from .database import engine as main_engine, normalize

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = lambda: os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MAX_ROWS = 50
# Optional: connect as the read-only `smartbiz_ai` role from supabase/schema.sql for database-level safety.
AI_URL = os.getenv("AI_DATABASE_URL")
ai_engine = create_engine(normalize(AI_URL), pool_pre_ping=True) if AI_URL else main_engine

class Unsafe(Exception):
    pass

def enabled() -> bool:
    return bool(API_KEY())

SQL_PROMPT = """You turn a small-business owner's question into ONE read-only {dialect} SQL query.
Rules: a single SELECT (or WITH ... SELECT) statement; no comments; use only the tables below and never the users table.
If the question cannot be answered from this data, or is not about the business, reply exactly NO_QUERY.
Output only the SQL, with no markdown. Money is in Indian rupees. Today is {today}.

Tables:
customers(id, name, phone, city)
suppliers(id, name, phone, item)
products(id, name, sku, stock, reorder_level, price)
expenses(id, title, category, amount, date)
orders(id, customer_id -> customers.id, stage, total, created_at)   -- stage 0 New, 1 Confirmed, 2 In Production, 3 Ready, 4 Delivered
order_items(id, order_id -> orders.id, product_id -> products.id, qty, unit_price)
payments(id, order_id -> orders.id, amount, note, paid_at)

Facts: an order's paid amount is SUM(payments.amount) for that order; pending = total - paid.
Active orders have stage < 4. A product is low on stock when stock <= reorder_level.

Example question: Who owes me the most?
SELECT c.name, SUM(o.total - COALESCE(p.paid, 0)) AS due FROM customers c JOIN orders o ON o.customer_id = c.id LEFT JOIN (SELECT order_id, SUM(amount) AS paid FROM payments GROUP BY order_id) p ON p.order_id = o.id GROUP BY c.name ORDER BY due DESC LIMIT 1"""

ANSWER_PROMPT = """You are SmartBiz, a friendly assistant for a small-business owner.
Answer the question in one to three short sentences using ONLY the data rows given.
Write money with the rupee sign and Indian digit grouping. If there are no rows, say nothing matched.
Never mention SQL or tables."""

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|execute|merge|attach|pragma|vacuum|set|into)\b", re.I)
BLOCKED = re.compile(r"\b(users|password_hash|pg_\w+|information_schema|sqlite_master)\b", re.I)

def _text(resp) -> str:
    c = resp.content
    return c if isinstance(c, str) else "".join(b.get("text", "") for b in c if isinstance(b, dict))

def clean(sql: str) -> str:
    sql = re.sub(r"^```(?:sql)?|```$", "", sql.strip(), flags=re.I | re.M).strip()
    return sql.rstrip(";").strip()

def check(sql: str) -> None:
    if ";" in sql or "--" in sql or "/*" in sql:
        raise Unsafe("Only a single plain query is allowed")
    if not re.match(r"^(select|with)\b", sql, re.I):
        raise Unsafe("Only SELECT queries are allowed")
    if FORBIDDEN.search(sql) or BLOCKED.search(sql):
        raise Unsafe("Query touches something that is not allowed")

def run(sql: str, eng=None) -> list[dict]:
    eng = eng or ai_engine
    pg = eng.dialect.name == "postgresql"
    with eng.connect() as conn:
        try:
            if pg:  # database-enforced: no writes, 5 second limit
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(text("SET LOCAL statement_timeout = '5000'"))
            else:
                conn.exec_driver_sql("PRAGMA query_only = ON")
            rows = conn.execute(text(sql)).mappings().fetchmany(MAX_ROWS)
            return [dict(r) for r in rows]
        finally:
            if not pg:
                conn.exec_driver_sql("PRAGMA query_only = OFF")

def ask(question: str, llm=None, eng=None) -> dict:
    if llm is None:
        opts = {} if MODEL.startswith("gemini-3") else {"temperature": 0}  # Gemini 3 works best at its default temperature
        llm = ChatGoogleGenerativeAI(model=MODEL, api_key=API_KEY(), timeout=30, **opts)
    eng = eng or ai_engine
    system = SQL_PROMPT.format(dialect=eng.dialect.name, today=dt.date.today().isoformat())
    msgs = [("system", system), ("human", question)]
    sql = clean(_text(llm.invoke(msgs)))
    if sql.upper().startswith("NO_QUERY"):
        return {"answer": "I can only answer questions about your orders, customers, stock, payments and expenses.",
                "sql": None, "rows": [], "mode": "llm"}
    for attempt in range(2):  # one automatic retry if the database rejects the query
        try:
            check(sql)
            rows = run(sql, eng)
            break
        except Unsafe:
            return {"answer": "I couldn't run that question safely. Try asking it a different way.",
                    "sql": None, "rows": [], "mode": "llm"}
        except SQLAlchemyError as e:
            if attempt == 1:
                raise
            err = str(getattr(e, "orig", e))[:300]
            sql = clean(_text(llm.invoke(msgs + [("ai", sql), ("human", f"That query failed: {err}. Return a corrected query only.")])))
    reply = llm.invoke([("system", ANSWER_PROMPT), ("human", f"Question: {question}\nRows: {json.dumps(rows, default=str)}")])
    return {"answer": _text(reply).strip(), "sql": sql, "rows": rows, "mode": "llm"}
