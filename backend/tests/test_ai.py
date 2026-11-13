import pytest
from sqlalchemy.exc import OperationalError
from app import ai
from app.database import engine
from conftest import owner_id

class FakeLLM:
    """Returns scripted replies and records the prompts it was given."""
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []
    def invoke(self, msgs):
        self.calls.append(msgs)
        r = self.replies.pop(0)
        return type("R", (), {"content": r})()

def shop(client, h, name):
    c = client.post("/api/customers", headers=h, json={"name": name}).json()
    p = client.post("/api/products", headers=h, json={"name": f"{name} item", "sku": "S1", "stock": 9, "reorder_level": 10, "price": 100}).json()
    client.post("/api/orders", headers=h, json={"customer_id": c["id"], "items": [{"product_id": p["id"], "qty": 2}]})

@pytest.mark.parametrize("sql", [
    "DELETE FROM customers", "SELECT 1; DROP TABLE customers", "SELECT * FROM users",
    "SELECT * FROM public.customers", "SELECT * FROM main.customers", 'SELECT * FROM "public"."orders"',
    "SELECT * FROM auth.users", "SELECT owner_id FROM customers", "SELECT sqlite_version()",
    "SELECT * FROM customers -- hi", "PRAGMA table_info(customers)", "SELECT pg_read_file('/etc/passwd')",
    "SELECT query_to_xml('select 1', true, true, '')", "WITH x AS (DELETE FROM orders RETURNING *) SELECT * FROM x",
])
def test_unsafe_sql_is_refused(sql):
    with pytest.raises(ai.Unsafe):
        ai.check(ai.clean(sql))

@pytest.mark.parametrize("sql", [
    "SELECT name FROM customers", "```sql\nSELECT c.name, o.total FROM customers c JOIN orders o ON o.customer_id = c.id;\n```",
    "WITH t AS (SELECT * FROM orders) SELECT COUNT(*) AS n FROM t", "SELECT title FROM expenses WHERE title LIKE '%rent%' ORDER BY date DESC LIMIT 5",
])
def test_safe_sql_is_allowed(sql):
    ai.check(ai.clean(sql))

def test_ai_only_sees_own_rows(client, user, other):
    shop(client, user, "Alpha")
    shop(client, other, "Beta")
    uid = owner_id(client, user)
    for sql in ["SELECT name FROM customers", "SELECT c.name FROM customers c JOIN orders o ON o.customer_id = c.id",
                "SELECT p.name FROM order_items i JOIN products p ON p.id = i.product_id",
                "WITH t AS (SELECT * FROM products) SELECT name FROM t ORDER BY name"]:
        names = {list(r.values())[0] for r in ai.run(sql, uid, engine)}
        assert names and all(n.startswith("Alpha") for n in names), (sql, names)

def test_ask_pipeline(client, user):
    shop(client, user, "Gamma")
    llm = FakeLLM("```sql\nSELECT name, stock FROM products\n```", "Gamma item has 7 left.")
    out = ai.ask("How much stock?", owner_id(client, user), llm=llm, eng=engine)
    assert out == {"answer": "Gamma item has 7 left.", "sql": "SELECT name, stock FROM products",
                   "rows": [{"name": "Gamma item", "stock": 7}], "mode": "llm"}
    assert "sqlite" in llm.calls[0][0][1]  # prompt names the SQL dialect

def test_ask_retries_a_broken_query_once(client, user):
    llm = FakeLLM("SELECT nope FROM customers", "SELECT COUNT(*) AS n FROM customers", "You have 0 customers.")
    out = ai.ask("How many customers?", owner_id(client, user), llm=llm, eng=engine)
    assert out["rows"] == [{"n": 0}] and "no such column" in llm.calls[1][-1][1]
    with pytest.raises(OperationalError):
        ai.ask("x?", 1, llm=FakeLLM("SELECT nope FROM customers", "SELECT nope2 FROM customers"), eng=engine)

def test_ask_refusals(client, user):
    uid = owner_id(client, user)
    assert ai.ask("Weather?", uid, llm=FakeLLM("NO_QUERY"), eng=engine)["sql"] is None
    out = ai.ask("Show users", uid, llm=FakeLLM("SELECT * FROM users"), eng=engine)
    assert "safely" in out["answer"] and out["rows"] == []

def test_db_left_writable_after_ai_query(client, user):
    ai.run("SELECT 1 AS x", owner_id(client, user), engine)
    assert client.post("/api/customers", headers=user, json={"name": "Still writable"}).status_code == 201

def test_model_fallback(monkeypatch):
    class Broken:
        def invoke(self, m): raise RuntimeError("503 UNAVAILABLE")
    g = ai.Gemini.__new__(ai.Gemini)
    g.models = [("main", Broken()), ("lite", FakeLLM("ok"))]
    monkeypatch.setattr(ai, "_down", {})
    assert g.invoke([]).content == "ok"
    assert [n for n, _ in g.models] == ["lite"] and "main" in ai._down

@pytest.mark.parametrize("q,expect", [
    ("Who owes me the most?", "owes you the most"),
    ("Which products are low on stock?", "Low on stock"),
    ("Which products have the lowest stock?", "Low on stock"),  # 'lowest' used to match 'owe'
    ("What is my total pending amount?", "pending payments"),
    ("Which orders are still in production?", "in production"),
    ("How much did I spend on expenses this month?", "this month"),
    ("What's my profit?", "Estimated profit"),
    ("Total sales?", "Total sales"),
    ("hello", "Try asking"),
])
def test_basic_mode_answers(client, user, q, expect):
    shop(client, user, "Delta")
    r = client.post("/api/ai/ask", headers=user, json={"question": q}).json()
    assert r["mode"] == "basic" and expect in r["answer"], r
    assert "not configured" in r["note"]

def test_llm_failure_falls_back_to_basic(client, user, monkeypatch):
    monkeypatch.setattr(ai, "enabled", lambda: True)
    def boom(*a, **k): raise RuntimeError("Gemini down")
    monkeypatch.setattr(ai, "ask", boom)
    r = client.post("/api/ai/ask", headers=user, json={"question": "total sales"}).json()
    assert r["mode"] == "basic" and "busy" in r["note"]
