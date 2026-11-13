"""One-time, idempotent upgrade for databases created before every account had its own workspace.

Older versions shared one set of business tables between all accounts (and shipped demo seed data).
Now each business table has an owner_id column. Rows created before that have no owner, so no
account sees them: every user starts with an empty dashboard.
"""
import logging
from sqlalchemy import inspect, text
from .database import Base

log = logging.getLogger("smartbiz.upgrade")
OWNED = ["customers", "suppliers", "products", "expenses", "orders"]
BUSINESS = ["payments", "order_items", "orders", "products", "expenses", "suppliers", "customers"]  # drop order

def upgrade(engine) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    missing = [t for t in OWNED if t in tables and "owner_id" not in {c["name"] for c in insp.get_columns(t)}]
    if missing:
        if engine.dialect.name == "sqlite":
            # SQLite cannot drop the old global UNIQUE(sku). The local file only held unowned rows that
            # nobody can see any more, so rebuild the business tables from scratch.
            log.warning("Upgrading local SQLite database: removing old shared demo data")
            with engine.begin() as c:
                for t in BUSINESS:
                    c.execute(text(f"DROP TABLE IF EXISTS {t}"))
            Base.metadata.create_all(engine)
        else:
            log.warning("Upgrading database: adding owner_id to %s", ", ".join(missing))
            with engine.begin() as c:
                for t in missing:
                    c.execute(text(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS owner_id integer REFERENCES users(id)"))
                    c.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{t}_owner_id ON {t}(owner_id)"))
                if "products" in missing:  # SKU is now unique per business, not globally
                    c.execute(text("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_sku_key"))
                    c.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_products_owner_sku ON products(owner_id, sku)"))
    with engine.begin() as c:  # every account is the owner (admin) of its own workspace
        c.execute(text("UPDATE users SET role = 'admin' WHERE role <> 'admin'"))
