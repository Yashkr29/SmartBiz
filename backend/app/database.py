import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

def normalize(url: str) -> str:
    """Supabase gives postgres:// or postgresql:// URIs; SQLAlchemy needs the driver name."""
    if url.startswith(("postgres://", "postgresql://")):
        return "postgresql+psycopg2://" + url.split("://", 1)[1]
    return url

raw_url = (os.getenv("DATABASE_URL") or "").strip()
if not raw_url or raw_url.startswith(("http://", "https://")):
    if raw_url.startswith(("http://", "https://")):
        print(f"[SmartBiz DB Warning] DATABASE_URL is set to an HTTP(S) URL ({raw_url}). SQLAlchemy requires a postgresql:// connection string. Falling back to local SQLite.")
    URL = "sqlite:///./smartbiz.db"
else:
    URL = normalize(raw_url)
sqlite = URL.startswith("sqlite")
engine = create_engine(URL, pool_pre_ping=True, connect_args={"check_same_thread": False} if sqlite else {})
if sqlite:  # make SQLite enforce foreign keys like PostgreSQL does
    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")
SessionLocal = sessionmaker(bind=engine, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
