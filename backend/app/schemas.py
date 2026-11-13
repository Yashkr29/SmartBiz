import datetime as dt
from pydantic import BaseModel, ConfigDict, EmailStr, Field

MAX_MONEY = 1_000_000_000  # fits numeric(12,2)
MAX_QTY = 1_000_000_000    # fits a 32-bit integer

class In(BaseModel):
    """Request bodies: trim text, refuse inf/NaN numbers."""
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# auth
class RegisterIn(In):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)
class LoginIn(In):
    email: EmailStr
    password: str = Field(max_length=64)
class UserOut(ORM):
    id: int; name: str; email: EmailStr; role: str
class TokenOut(BaseModel):
    access_token: str; token_type: str = "bearer"; user: UserOut

# master data
class CustomerIn(In):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(default="", max_length=30)
    city: str = Field(default="", max_length=80)
class CustomerOut(ORM):
    id: int; name: str; phone: str; city: str; due: float = 0
class SupplierIn(In):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(default="", max_length=30)
    item: str = Field(default="", max_length=200)
class SupplierOut(ORM):
    id: int; name: str; phone: str; item: str
class ProductIn(In):
    name: str = Field(min_length=1, max_length=120)
    sku: str = Field(min_length=1, max_length=40)
    stock: int = Field(default=0, ge=0, le=MAX_QTY)
    reorder_level: int = Field(default=0, ge=0, le=MAX_QTY)
    price: float = Field(default=0, ge=0, le=MAX_MONEY)
class ProductOut(ORM):
    id: int; name: str; sku: str; stock: int; reorder_level: int; price: float
class ExpenseIn(In):
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(default="General", max_length=60)
    amount: float = Field(gt=0, le=MAX_MONEY)
    date: dt.date = Field(default_factory=dt.date.today)
class ExpenseOut(ORM):
    id: int; title: str; category: str; amount: float; date: dt.date

# orders
class ItemIn(In):
    product_id: int; qty: int = Field(gt=0, le=MAX_QTY)
class OrderCreate(In):
    customer_id: int; items: list[ItemIn] = Field(min_length=1, max_length=100)
    advance: float = Field(default=0, ge=0, le=MAX_MONEY)
class PaymentIn(In):
    amount: float = Field(gt=0, le=MAX_MONEY); note: str = Field(default="", max_length=120)
class ItemOut(BaseModel):
    product_id: int; product: str; qty: int; unit_price: float
class PaymentOut(ORM):
    amount: float; note: str; paid_at: dt.datetime
class OrderOut(BaseModel):
    id: int; code: str; customer_id: int; customer: str
    total: float; paid: float; pending: float
    stage: int; stage_name: str; created_at: dt.datetime
    items: list[ItemOut]; payments: list[PaymentOut]

class AskIn(In):
    question: str = Field(min_length=2, max_length=300)
