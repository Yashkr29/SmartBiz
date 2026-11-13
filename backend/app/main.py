import logging, os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .upgrade import upgrade
from .routers import auth, crud, orders, insights, imports

logging.basicConfig(level=logging.INFO)
Base.metadata.create_all(engine)  # use Alembic migrations once the schema settles
upgrade(engine)

app = FastAPI(title="SmartBiz API", version="0.2.0")
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
    return {"status": "ok"}
