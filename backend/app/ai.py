"""AI business Q&A: question -> LLM writes SQL -> validated, read-only, per-account execution -> LLM explains the rows."""
import datetime as dt, json, logging, os, re, time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from .database import engine as main_engine, normalize

log = logging.getLogger("smartbiz.ai")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Tried when the main model is overloaded (503) or times out (504). Empty string disables it.
FALLBACK = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-lite-latest")
TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "25"))
API_KEY = lambda: os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MAX_ROWS = 50
COOLDOWN = 120  # seconds to skip a model after it failed
# Optional: connect as the read-only `smartbiz_ai` role from supabase/schema.sql for database-level safety.
AI_URL = os.getenv("AI_DATABASE_URL")
ai_engine = create_engine(normalize(AI_URL), pool_pre_ping=True) if AI_URL else main_engine

class Unsafe(Exception):
    pass

def enabled() -> bool:
    return bool(API_KEY())

SQL_PROMPT = """You turn a small-business owner's question into ONE read-only {dialect} SQL query.
Rules: a single SELECT (or WITH ... SELECT) statement; no comments; use only the tables below, unqualified (no schema prefix).
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
Order codes shown to the user look like ORD-1001, which is orders.id + 1000.

Example question: Who owes me the most?
SELECT c.name, SUM(o.total - COALESCE(p.paid, 0)) AS due FROM customers c JOIN orders o ON o.customer_id = c.id LEFT JOIN (SELECT order_id, SUM(amount) AS paid FROM payments GROUP BY order_id) p ON p.order_id = o.id GROUP BY c.name ORDER BY due DESC LIMIT 1"""

ANSWER_PROMPT = """You are SmartBiz, a friendly assistant for a small-business owner.
Answer the question in one to three short sentences using ONLY the data rows given.
Write money with the rupee sign and Indian digit grouping. If there are no rows, say nothing matched.
Never mention SQL or tables."""

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|execute|merge|attach|detach|"
                       r"pragma|vacuum|set|into|reindex|analyze|listen|notify|lock|do)\b", re.I)
BLOCKED = re.compile(r"\b(users|password_hash|owner_id|pg_\w+|information_schema|sqlite_\w+|current_setting|set_config|"
                     r"dblink\w*|lo_\w+|\w+_to_xml\w*|load_extension|readfile|writefile|fts3_tokenizer)\b", re.I)
# Schema-qualified names would bypass the per-account views below, so they are never allowed.
SCHEMA = re.compile(r"[\"`\[]?\b(public|main|temp|auth|storage|extensions|realtime|vault|graphql\w*|pgsodium\w*|net|cron|"
                    r"supabase_\w+)\b[\"`\]]?\s*\.", re.I)

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
    if FORBIDDEN.search(sql) or BLOCKED.search(sql) or SCHEMA.search(sql) or re.search(r"\bu&[\"']", sql, re.I):
        raise Unsafe("Query touches something that is not allowed")

def scoped(sql: str, owner_id: int, dialect: str) -> str:
    """Wrap the query so every table name resolves to a view of this account's rows only."""
    o, s = int(owner_id), ("main." if dialect == "sqlite" else "public.")
    own_orders = f"SELECT id FROM {s}orders WHERE owner_id = {o}"
    views = {
        "customers": f"SELECT id, name, phone, city FROM {s}customers WHERE owner_id = {o}",
        "suppliers": f"SELECT id, name, phone, item FROM {s}suppliers WHERE owner_id = {o}",
        "products": f"SELECT id, name, sku, stock, reorder_level, price FROM {s}products WHERE owner_id = {o}",
        "expenses": f"SELECT id, title, category, amount, date FROM {s}expenses WHERE owner_id = {o}",
        "orders": f"SELECT id, customer_id, stage, total, created_at FROM {s}orders WHERE owner_id = {o}",
        "order_items": f"SELECT id, order_id, product_id, qty, unit_price FROM {s}order_items WHERE order_id IN ({own_orders})",
        "payments": f"SELECT id, order_id, amount, note, paid_at FROM {s}payments WHERE order_id IN ({own_orders})",
    }
    ctes = ", ".join(f"{name} AS ({q})" for name, q in views.items())
    return f"WITH {ctes} SELECT * FROM ({sql}) AS answer"

def run(sql: str, owner_id: int, eng=None) -> list[dict]:
    eng = eng or ai_engine
    pg = eng.dialect.name == "postgresql"
    with eng.connect() as conn:
        try:
            if pg:  # database-enforced: no writes, 5 second limit
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(text("SET LOCAL statement_timeout = '5000'"))
            else:
                conn.exec_driver_sql("PRAGMA query_only = ON")
            rows = conn.execute(text(scoped(sql, owner_id, eng.dialect.name))).mappings().fetchmany(MAX_ROWS)
            return [dict(r) for r in rows]
        finally:
            if not pg:
                conn.exec_driver_sql("PRAGMA query_only = OFF")

_down: dict[str, float] = {}  # model -> time it may be tried again

class Gemini:
    """Calls the main model and switches to the fallback model if it is overloaded or slow."""
    def __init__(self):
        from langchain_google_genai import ChatGoogleGenerativeAI
        names = [MODEL] + ([FALLBACK] if FALLBACK and FALLBACK != MODEL else [])
        self.models = []
        for name in names:
            opts = {} if name.startswith("gemini-3") else {"temperature": 0}  # Gemini 3 prefers its default temperature
            self.models.append((name, ChatGoogleGenerativeAI(model=name, api_key=API_KEY(), timeout=TIMEOUT, max_retries=1, **opts)))

    def invoke(self, msgs):
        now, last = time.time(), None
        ready = [x for x in self.models if _down.get(x[0], 0) <= now] or self.models
        for name, llm in ready:
            try:
                return llm.invoke(msgs)
            except Exception as e:  # overloaded, timed out, model retired, network...
                log.warning("Gemini model %s failed: %s", name, str(e)[:200])
                _down[name], last = time.time() + COOLDOWN, e
                self.models = [x for x in self.models if x[0] != name] or self.models  # stick with what works for this request
        raise last

def ask(question: str, owner_id: int, llm=None, eng=None) -> dict:
    llm = llm or Gemini()
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
            rows = run(sql, owner_id, eng)
            break
        except Unsafe:
            log.warning("Refused AI query: %s", sql[:300])
            return {"answer": "I couldn't run that question safely. Try asking it a different way.",
                    "sql": None, "rows": [], "mode": "llm"}
        except SQLAlchemyError as e:
            if attempt == 1:
                raise
            err = str(getattr(e, "orig", e)).split("\n")[0][:300]
            sql = clean(_text(llm.invoke(msgs + [("ai", sql), ("human", f"That query failed: {err}. Return a corrected query only.")])))
    reply = llm.invoke([("system", ANSWER_PROMPT), ("human", f"Question: {question}\nRows: {json.dumps(rows, default=str)}")])
    return {"answer": _text(reply).strip() or "I found the data but could not word an answer. Open the details below.",
            "sql": sql, "rows": rows, "mode": "llm"}
