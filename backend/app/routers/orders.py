from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import current_user, admin_only
from .. import models as m, schemas as s

router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[Depends(current_user)])

def render(o: m.Order) -> s.OrderOut:
    return s.OrderOut(
        id=o.id, code=f"ORD-{1000 + o.id}", customer_id=o.customer_id, customer=o.customer.name,
        total=o.total, paid=o.paid, pending=o.pending, stage=o.stage, stage_name=m.STAGES[o.stage],
        created_at=o.created_at, payments=o.payments,
        items=[s.ItemOut(product_id=i.product_id, product=i.product.name, qty=i.qty, unit_price=i.unit_price) for i in o.items])

def find(db, id) -> m.Order:
    o = db.get(m.Order, id)
    if not o:
        raise HTTPException(404, "Order not found")
    return o

@router.get("", response_model=list[s.OrderOut])
def list_orders(db: Session = Depends(get_db)):
    return [render(o) for o in db.query(m.Order).order_by(m.Order.id.desc())]

@router.get("/{id}", response_model=s.OrderOut)
def get_order(id: int, db: Session = Depends(get_db)):
    return render(find(db, id))

@router.post("", response_model=s.OrderOut, status_code=201)
def create_order(body: s.OrderCreate, db: Session = Depends(get_db)):
    if not db.get(m.Customer, body.customer_id):
        raise HTTPException(404, "Customer not found")
    qty = defaultdict(int)
    for i in body.items:
        qty[i.product_id] += i.qty
    order = m.Order(customer_id=body.customer_id, total=0)
    for pid, q in qty.items():
        p = db.get(m.Product, pid)
        if not p:
            raise HTTPException(404, f"Product {pid} not found")
        if p.stock < q:
            raise HTTPException(422, f"Only {p.stock} of {p.name} in stock")
        p.stock -= q  # inventory updates with the order; rolled back automatically if anything below fails
        order.items.append(m.OrderItem(product_id=pid, qty=q, unit_price=p.price))
        order.total += p.price * q
    if round(body.advance, 2) > round(order.total, 2):
        raise HTTPException(422, "Advance cannot exceed the order total")
    if body.advance:
        order.payments.append(m.Payment(amount=body.advance, note="Advance"))
    db.add(order); db.commit(); db.refresh(order)
    return render(order)

@router.post("/{id}/payments", response_model=s.OrderOut, status_code=201)
def add_payment(id: int, body: s.PaymentIn, db: Session = Depends(get_db)):
    o = find(db, id)
    if round(body.amount, 2) > o.pending:
        raise HTTPException(422, f"Payment exceeds the pending amount of {o.pending:.2f}")
    o.payments.append(m.Payment(amount=body.amount, note=body.note))
    db.commit(); db.refresh(o)
    return render(o)

@router.post("/{id}/advance", response_model=s.OrderOut)
def advance_stage(id: int, db: Session = Depends(get_db)):
    o = find(db, id)
    if o.stage >= len(m.STAGES) - 1:
        raise HTTPException(409, "Order is already delivered")
    o.stage += 1
    db.commit(); db.refresh(o)
    return render(o)

@router.delete("/{id}", status_code=204, dependencies=[Depends(admin_only)])
def delete_order(id: int, db: Session = Depends(get_db)):
    o = find(db, id)
    if o.stage < len(m.STAGES) - 1:  # not delivered yet: put stock back
        for i in o.items:
            i.product.stock += i.qty
    db.delete(o); db.commit()
