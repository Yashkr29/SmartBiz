import datetime as dt
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

STAGES = ["New", "Confirmed", "In Production", "Ready", "Delivered"]

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(String(20), default="staff")  # admin | staff

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(30), default="")
    city: Mapped[str] = mapped_column(String(80), default="")

class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(30), default="")
    item: Mapped[str] = mapped_column(String(200), default="")

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    stock: Mapped[int] = mapped_column(default=0)
    reorder_level: Mapped[int] = mapped_column(default=0)
    price: Mapped[float] = mapped_column(default=0)

class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60), default="General")
    amount: Mapped[float]
    date: Mapped[dt.date] = mapped_column(default=dt.date.today)

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    stage: Mapped[int] = mapped_column(default=0)
    total: Mapped[float] = mapped_column(default=0)
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
    customer: Mapped[Customer] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(cascade="all, delete-orphan")

    @property
    def paid(self): return round(sum(p.amount for p in self.payments), 2)
    @property
    def pending(self): return round(self.total - self.paid, 2)

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int]
    unit_price: Mapped[float]
    product: Mapped[Product] = relationship()

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    amount: Mapped[float]
    note: Mapped[str] = mapped_column(String(120), default="")
    paid_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
