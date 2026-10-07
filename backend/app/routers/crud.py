from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import current_user, admin_only
from .. import models as m, schemas as s

def crud_router(prefix, Model, In, Out, decorate=None):
    """List (with ?q= search), create, update, delete (admin only) for a simple table."""
    r = APIRouter(prefix=prefix, tags=[prefix.strip("/")], dependencies=[Depends(current_user)])

    def render(db, obj):
        out = Out.model_validate(obj)
        return decorate(db, out) if decorate else out

    def commit(db):
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Duplicate value, or this record is still in use")

    def find(db, id):
        obj = db.get(Model, id)
        if not obj:
            raise HTTPException(404, "Not found")
        return obj

    @r.get("", response_model=list[Out])
    def list_all(q: str = "", db: Session = Depends(get_db)):
        rows = [render(db, x) for x in db.query(Model).order_by(Model.id.desc())]
        return [x for x in rows if q.lower() in str(x.model_dump()).lower()] if q else rows

    @r.post("", response_model=Out, status_code=201)
    def create(body: In, db: Session = Depends(get_db)):
        obj = Model(**body.model_dump()); db.add(obj); commit(db); db.refresh(obj)
        return render(db, obj)

    @r.put("/{id}", response_model=Out)
    def update(id: int, body: In, db: Session = Depends(get_db)):
        obj = find(db, id)
        for k, v in body.model_dump().items():
            setattr(obj, k, v)
        commit(db); db.refresh(obj)
        return render(db, obj)

    @r.delete("/{id}", status_code=204, dependencies=[Depends(admin_only)])
    def delete(id: int, db: Session = Depends(get_db)):
        db.delete(find(db, id)); commit(db)

    return r

def with_due(db, out):  # outstanding balance across a customer's orders
    out.due = round(sum(o.pending for o in db.query(m.Order).filter_by(customer_id=out.id)), 2)
    return out

customers = crud_router("/customers", m.Customer, s.CustomerIn, s.CustomerOut, with_due)
suppliers = crud_router("/suppliers", m.Supplier, s.SupplierIn, s.SupplierOut)
products = crud_router("/products", m.Product, s.ProductIn, s.ProductOut)
expenses = crud_router("/expenses", m.Expense, s.ExpenseIn, s.ExpenseOut)
