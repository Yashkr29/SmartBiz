import sqlite3
from sqlalchemy import create_engine, inspect
from app.database import Base
from app.upgrade import upgrade

OLD_SCHEMA = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100), email VARCHAR(255) UNIQUE, password_hash VARCHAR, role VARCHAR(20));
CREATE TABLE customers (id INTEGER PRIMARY KEY, name VARCHAR(120), phone VARCHAR(30), city VARCHAR(80));
CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(120), sku VARCHAR(40) UNIQUE, stock INTEGER, reorder_level INTEGER, price FLOAT);
INSERT INTO users VALUES (1, 'Demo', 'demo@smartbiz.com', 'x', 'admin'), (2, 'Later', 'l@x.com', 'x', 'staff');
INSERT INTO customers VALUES (1, 'Asha Traders', '', 'Pune');
INSERT INTO products VALUES (1, 'Teak Table', 'TST-01', 3, 5, 12500);
"""

def test_old_shared_sqlite_database_is_upgraded(tmp_path):
    path = tmp_path / "old.db"
    con = sqlite3.connect(path); con.executescript(OLD_SCHEMA); con.close()
    eng = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(eng)
    upgrade(eng)
    upgrade(eng)  # running twice is harmless
    insp = inspect(eng)
    for t in ("customers", "products", "orders", "expenses", "suppliers"):
        assert "owner_id" in {c["name"] for c in insp.get_columns(t)}
    con = sqlite3.connect(path)
    assert con.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0  # shared demo data is gone
    assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2       # accounts are kept
    assert {r[0] for r in con.execute("SELECT role FROM users")} == {"admin"}
    # the same SKU is allowed for two different owners now
    con.execute("INSERT INTO products (owner_id, name, sku, stock, reorder_level, price) VALUES (1,'a','S',0,0,0), (2,'b','S',0,0,0)")
    con.close()
