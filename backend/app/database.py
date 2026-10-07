import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

def normalize(url: str) -> str:
    """Supabase gives postgres:// or postgresql:// URIs; SQLAlchemy needs the driver name."""
    if url.startswith(("postgres://", "postgresql://")):
        return "postgresql+psycopg2://" + url.split("://", 1)[1]
    return url

URL = normalize(os.getenv("DATABASE_URL", "sqlite:///./smartbiz.db"))
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
