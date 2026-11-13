from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from ..database import get_db
from ..security import current_user, admin_only
from .. import models as m, schemas as s

def commit(db: Session, msg="Duplicate value, or this record is still in use"):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, msg)

def crud_router(prefix, Model, In, Out, decorate=None):
    """List (with ?q= search), create, update, delete (admin only) for a simple table.
    Every query is limited to the logged-in user's own rows."""
    r = APIRouter(prefix=prefix, tags=[prefix.strip("/")])

    def render(db, user, objs):
        outs = [Out.model_validate(o) for o in objs]
        return decorate(db, user, outs) if decorate else outs

    def find(db, user, id):
        obj = db.get(Model, id)
        if not obj or obj.owner_id != user.id:
            raise HTTPException(404, "Not found")
        return obj

    @r.get("", response_model=list[Out])
    def list_all(q: str = "", db: Session = Depends(get_db), user: m.User = Depends(current_user)):
        rows = render(db, user, db.query(Model).filter_by(owner_id=user.id).order_by(Model.id.desc()))
        q = q.strip().lower()
        return [x for x in rows if any(q in str(v).lower() for v in x.model_dump().values())] if q else rows

    @r.post("", response_model=Out, status_code=201)
    def create(body: In, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
        obj = Model(**body.model_dump(), owner_id=user.id); db.add(obj); commit(db); db.refresh(obj)
        return render(db, user, [obj])[0]

    @r.put("/{id}", response_model=Out)
    def update(id: int, body: In, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
        obj = find(db, user, id)
        for k, v in body.model_dump().items():
            setattr(obj, k, v)
        commit(db); db.refresh(obj)
        return render(db, user, [obj])[0]

    @r.delete("/{id}", status_code=204)
    def delete(id: int, db: Session = Depends(get_db), user: m.User = Depends(admin_only)):
        db.delete(find(db, user, id)); commit(db, "This record is used by an order, so it cannot be deleted")

    return r

def with_due(db, user, outs):
    """Outstanding balance across each customer's orders, computed in one pass (no query per customer)."""
    due = defaultdict(float)
    for o in db.query(m.Order).filter_by(owner_id=user.id).options(selectinload(m.Order.payments)):
        due[o.customer_id] += o.pending
    for out in outs:
        out.due = round(due[out.id], 2)
    return outs

customers = crud_router("/customers", m.Customer, s.CustomerIn, s.CustomerOut, with_due)
suppliers = crud_router("/suppliers", m.Supplier, s.SupplierIn, s.SupplierOut)
products = crud_router("/products", m.Product, s.ProductIn, s.ProductOut)
expenses = crud_router("/expenses", m.Expense, s.ExpenseIn, s.ExpenseOut)
