import datetime as dt, logging, os, re
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from ..database import get_db
from ..security import current_user
from .. import ai, models as m, schemas as s

router = APIRouter(tags=["insights"])
log = logging.getLogger("smartbiz.ai")
inr = lambda n: f"₹{n:,.0f}"
# Dates on the dashboard follow the business's clock (default India, UTC+5:30); orders are stored in UTC.
LOCAL_TZ = dt.timezone(dt.timedelta(minutes=int(os.getenv("TZ_OFFSET_MINUTES", "330"))))

def local_date(t: dt.datetime) -> dt.date:
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(LOCAL_TZ).date()

def snapshot(db: Session, user: m.User) -> dict:
    orders = (db.query(m.Order).filter_by(owner_id=user.id)
              .options(selectinload(m.Order.payments), selectinload(m.Order.customer)).all())
    sales = round(sum(o.total for o in orders), 2)
    expenses = round(float(db.query(func.coalesce(func.sum(m.Expense.amount), 0)).filter(m.Expense.owner_id == user.id).scalar()), 2)
    low = (db.query(m.Product).filter(m.Product.owner_id == user.id, m.Product.stock <= m.Product.reorder_level)
           .order_by(m.Product.stock).all())
    return {"orders": orders, "sales": sales, "expenses": expenses, "low": low,
            "pending": round(sum(o.pending for o in orders), 2)}

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    d = snapshot(db, user)
    today = dt.datetime.now(LOCAL_TZ).date()
    days = [today - dt.timedelta(days=i) for i in range(6, -1, -1)]
    per_day = defaultdict(int)
    for o in d["orders"]:
        per_day[local_date(o.created_at)] += 1
    return {
        "total_sales": d["sales"], "active_orders": sum(o.stage < 4 for o in d["orders"]),
        "pending_payments": d["pending"], "expenses": d["expenses"],
        "estimated_profit": round(d["sales"] - d["expenses"], 2),
        "low_stock": [{"id": p.id, "name": p.name, "stock": p.stock} for p in d["low"]],
        "weekly_orders": [{"d": x.strftime("%a"), "v": per_day[x]} for x in days],
        "counts": {"orders": len(d["orders"]),
                   "customers": db.query(m.Customer).filter_by(owner_id=user.id).count(),
                   "products": db.query(m.Product).filter_by(owner_id=user.id).count()},
    }

def has(q: str, *words) -> bool:
    return any(re.search(rf"\b{w}", q) for w in words)

def basic_answer(q: str, d: dict, db: Session, user: m.User) -> str:
    if has(q, "owe", "owing", "due", "debt"):
        owed = defaultdict(float)
        for o in d["orders"]:
            owed[o.customer.name] += o.pending
        name, amt = max(owed.items(), key=lambda kv: kv[1], default=(None, 0))
        return f"{name} owes you the most: {inr(amt)}." if amt > 0 else "Nobody owes you anything right now."
    if has(q, "stock", "inventory", "restock", "reorder"):
        names = ", ".join(f"{p.name} ({p.stock} left)" for p in d["low"])
        return f"Low on stock: {names}." if names else "Every product is above its reorder level."
    if has(q, "production", "progress", "active", "open order", "pending order", "not delivered", "stage"):
        active = [o for o in d["orders"] if o.stage < 4]
        if has(q, "production"):
            active = [o for o in active if o.stage == 2]
            label = "in production"
        else:
            label = "still active"
        codes = ", ".join(f"ORD-{1000 + o.id} ({o.customer.name})" for o in active[:10])
        return f"{len(active)} order(s) {label}: {codes}." if active else f"No orders are {label} right now."
    if has(q, "pending", "receivable", "outstanding", "unpaid"):
        return f"Total pending payments: {inr(d['pending'])}."
    if has(q, "profit", "margin", "earn"):
        return f"Estimated profit is {inr(d['sales'] - d['expenses'])} (sales {inr(d['sales'])} minus expenses {inr(d['expenses'])})."
    if has(q, "expense", "spend", "spent", "cost"):
        if has(q, "month"):
            start = dt.datetime.now(LOCAL_TZ).date().replace(day=1)
            total = db.query(func.coalesce(func.sum(m.Expense.amount), 0)).filter(
                m.Expense.owner_id == user.id, m.Expense.date >= start).scalar()
            return f"You spent {inr(float(total))} this month."
        return f"Total expenses so far: {inr(d['expenses'])}."
    if has(q, "sales", "sold", "revenue", "turnover", "income"):
        return f"Total sales so far: {inr(d['sales'])} across {len(d['orders'])} order(s)."
    if has(q, "how many order", "number of order", "orders"):
        return f"You have {len(d['orders'])} order(s), {sum(o.stage < 4 for o in d['orders'])} of them active."
    return "Try asking who owes you, which products are low on stock, orders in production, pending payments, expenses, sales or profit."

@router.post("/ai/ask")
def ask(body: s.AskIn, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    """Uses the LLM pipeline in app/ai.py when GOOGLE_API_KEY is set; otherwise (or if the LLM
    call fails) falls back to simple keyword rules so the assistant always answers."""
    note = None
    if ai.enabled():
        try:
            return ai.ask(body.question, user.id)
        except Exception:
            log.exception("LLM pipeline failed, using basic mode")
            note = "The AI service is busy or unreachable, so this is a basic answer."
    else:
        note = "AI is not configured (GOOGLE_API_KEY is empty), so this is a basic answer."
    answer = basic_answer(body.question.lower(), snapshot(db, user), db, user)
    return {"answer": answer, "sql": None, "rows": [], "mode": "basic", "note": note}
