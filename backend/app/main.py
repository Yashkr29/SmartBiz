import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routers import auth, crud, orders, insights

Base.metadata.create_all(engine)  # use Alembic migrations once the schema settles

app = FastAPI(title="SmartBiz API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, crud.customers, crud.suppliers, crud.products, crud.expenses, orders.router, insights.router):
    app.include_router(r, prefix="/api")

@app.get("/api/health")
def health():
    return {"status": "ok"}
