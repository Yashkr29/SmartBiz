"""Demo data matching the frontend mock. Login: demo@smartbiz.com / demo1234"""
from app.database import Base, engine, SessionLocal
from app import models as m
from app.security import hash_pw

Base.metadata.create_all(engine)
db = SessionLocal()
if not db.query(m.User).first():
    db.add(m.User(name="Demo Owner", email="demo@smartbiz.com", password_hash=hash_pw("demo1234"), role="admin"))
    db.add_all([m.Customer(name="Asha Traders", phone="98220 11234", city="Pune"),
                m.Customer(name="Rohan Interiors", phone="98901 55621", city="Mumbai")])
    db.add_all([m.Product(name="Teak Study Table", sku="TST-01", stock=3, reorder_level=5, price=12500),
                m.Product(name="Cane Chair", sku="CNC-07", stock=2, reorder_level=6, price=4200),
                m.Product(name="Wall Shelf", sku="WSH-03", stock=25, reorder_level=10, price=2600)])
    db.add(m.Expense(title="Raw material", category="Supplies", amount=64000))
    db.commit()
    print("Seeded. Create orders through the API so stock and payments stay consistent.")
else:
    print("Database already has data, nothing to do.")
