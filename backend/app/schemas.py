import datetime as dt
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# auth
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)
class LoginIn(BaseModel):
    email: EmailStr
    password: str
class UserOut(ORM):
    id: int; name: str; email: EmailStr; role: str
class TokenOut(BaseModel):
    access_token: str; token_type: str = "bearer"; user: UserOut

# master data
class CustomerIn(BaseModel):
    name: str = Field(min_length=1); phone: str = ""; city: str = ""
class CustomerOut(CustomerIn, ORM):
    id: int; due: float = 0
class SupplierIn(BaseModel):
    name: str = Field(min_length=1); phone: str = ""; item: str = ""
class SupplierOut(SupplierIn, ORM):
    id: int
class ProductIn(BaseModel):
    name: str = Field(min_length=1); sku: str = Field(min_length=1)
    stock: int = Field(ge=0); reorder_level: int = Field(ge=0); price: float = Field(ge=0)
class ProductOut(ProductIn, ORM):
    id: int
class ExpenseIn(BaseModel):
    title: str = Field(min_length=1); category: str = "General"
    amount: float = Field(gt=0); date: dt.date = Field(default_factory=dt.date.today)
class ExpenseOut(ExpenseIn, ORM):
    id: int

# orders
class ItemIn(BaseModel):
    product_id: int; qty: int = Field(gt=0)
class OrderCreate(BaseModel):
    customer_id: int; items: list[ItemIn] = Field(min_length=1); advance: float = Field(default=0, ge=0)
class PaymentIn(BaseModel):
    amount: float = Field(gt=0); note: str = ""
class ItemOut(BaseModel):
    product_id: int; product: str; qty: int; unit_price: float
class PaymentOut(ORM):
    amount: float; note: str; paid_at: dt.datetime
class OrderOut(BaseModel):
    id: int; code: str; customer_id: int; customer: str
    total: float; paid: float; pending: float
    stage: int; stage_name: str; created_at: dt.datetime
    items: list[ItemOut]; payments: list[PaymentOut]

class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=300)
