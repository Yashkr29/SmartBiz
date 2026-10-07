import datetime as dt, logging
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import current_user
from .. import ai, models as m, schemas as s

router = APIRouter(tags=["insights"], dependencies=[Depends(current_user)])
inr = lambda n: f"₹{n:,.0f}"

def snapshot(db: Session) -> dict:
    orders = db.query(m.Order).all()
    sales = sum(o.total for o in orders)
    expenses = db.query(func.coalesce(func.sum(m.Expense.amount), 0)).scalar()
    low = db.query(m.Product).filter(m.Product.stock <= m.Product.reorder_level).all()
    return {"orders": orders, "sales": sales, "expenses": expenses, "low": low,
            "pending": sum(o.pending for o in orders)}

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    d = snapshot(db)
    today = dt.date.today()
    days = [today - dt.timedelta(days=i) for i in range(6, -1, -1)]
    per_day = defaultdict(int)
    for o in d["orders"]:
        per_day[o.created_at.date()] += 1
    return {
        "total_sales": d["sales"], "active_orders": sum(o.stage < 4 for o in d["orders"]),
        "pending_payments": d["pending"], "expenses": d["expenses"],
        "estimated_profit": d["sales"] - d["expenses"],
        "low_stock": [{"id": p.id, "name": p.name, "stock": p.stock} for p in d["low"]],
        "weekly_orders": [{"d": x.strftime("%a"), "v": per_day[x]} for x in days],
    }

def basic_answer(q: str, d: dict) -> str:
    if "owe" in q:
        owed = defaultdict(float)
        for o in d["orders"]:
            owed[o.customer.name] += o.pending
        name, amt = max(owed.items(), key=lambda kv: kv[1], default=(None, 0))
        return f"{name} owes you the most: {inr(amt)}." if amt > 0 else "Nobody owes you anything right now."
    if "stock" in q:
        names = ", ".join(p.name for p in d["low"])
        return f"Low on stock: {names}." if names else "Every product is above its reorder level."
    if "pending" in q:
        return f"Total pending payments: {inr(d['pending'])}."
    if "profit" in q:
        return f"Estimated profit is {inr(d['sales'] - d['expenses'])} (sales {inr(d['sales'])} minus expenses {inr(d['expenses'])})."
    if "sales" in q:
        return f"Total sales so far: {inr(d['sales'])}."
    return "Try asking who owes you, which products are low on stock, pending payments, sales or profit."

@router.post("/ai/ask")
def ask(body: s.AskIn, db: Session = Depends(get_db)):
    """Uses the LLM pipeline in app/ai.py when GOOGLE_API_KEY is set; otherwise (or if the LLM
    call fails) falls back to simple keyword rules so the assistant always answers."""
    if ai.enabled():
        try:
            return ai.ask(body.question)
        except Exception:
            logging.getLogger("smartbiz.ai").exception("LLM pipeline failed, using basic mode")
    return {"answer": basic_answer(body.question.lower(), snapshot(db)), "sql": None, "rows": [], "mode": "basic"}
