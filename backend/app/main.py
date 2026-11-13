import logging, os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from .database import Base, engine
from .upgrade import upgrade
from .routers import auth, crud, orders, insights, imports

logging.basicConfig(level=logging.INFO)
Base.metadata.create_all(engine)  # use Alembic migrations once the schema settles
upgrade(engine)

app = FastAPI(title="SmartBiz API", version="0.2.0")
log = logging.getLogger("smartbiz")

# Registered before CORS so it sits inside it: a crash becomes a JSON 500 that still carries CORS
# headers. Without this the browser hides the real error behind a misleading "blocked by CORS policy".
@app.middleware("http")
async def errors_as_json(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Server error. Please try again, or check the backend logs."}, status_code=500)

raw_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if not raw_origins or "*" in raw_origins:
    origins = ["*"]
else:
    origins = list(set(raw_origins + ["http://localhost:5173", "http://127.0.0.1:5173"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$" if origins != ["*"] else None,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, crud.customers, crud.suppliers, crud.products, crud.expenses, orders.router,
          insights.router, imports.router):
    app.include_router(r, prefix="/api")

@app.get("/api/health")
def health():
    """Also reports whether the database answers, to make deployment problems easy to spot."""
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        db = "ok"
    except Exception as e:
        log.warning("Health check: database unreachable: %s", e)
        db = "unreachable"
    return {"status": "ok", "database": engine.dialect.name, "database_status": db}
