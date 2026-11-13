"""CSV import for customers, products, suppliers and expenses.

POST /import/{entity}?commit=false  -> preview: column mapping, row errors, first rows (nothing saved)
POST /import/{entity}?commit=true   -> same checks, then saves every valid row in one transaction
"""
import csv, datetime as dt, io, re
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import current_user
from .. import models as m, schemas as s
from .crud import commit as safe_commit

router = APIRouter(prefix="/import", tags=["import"])
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000

# field -> (type, accepted header names). Headers are compared lower-case with spaces/punctuation removed.
PHONE = ["phone", "mobile", "mobileno", "mobilenumber", "phoneno", "phonenumber", "contact", "contactno",
         "contactnumber", "whatsapp", "tel", "telephone", "cell"]
SPECS = {
    "customers": (m.Customer, s.CustomerIn, {
        "name": ("text", ["name", "customer", "customername", "client", "clientname", "fullname", "party", "partyname", "buyer"]),
        "phone": ("phone", PHONE),
        "city": ("text", ["city", "town", "location", "place", "district", "area"]),
    }),
    "suppliers": (m.Supplier, s.SupplierIn, {
        "name": ("text", ["name", "supplier", "suppliername", "vendor", "vendorname", "company", "companyname", "party", "partyname"]),
        "phone": ("phone", PHONE),
        "item": ("text", ["item", "items", "supplies", "supplied", "product", "products", "material", "materials", "goods", "category"]),
    }),
    "products": (m.Product, s.ProductIn, {
        "name": ("text", ["name", "product", "productname", "item", "itemname", "title"]),
        "sku": ("text", ["sku", "skucode", "code", "productcode", "itemcode", "barcode", "productid", "itemid", "partno", "partnumber"]),
        "stock": ("int", ["stock", "qty", "quantity", "instock", "stockqty", "stockquantity", "onhand", "available", "units", "currentstock", "opening", "openingstock"]),
        "reorder_level": ("int", ["reorderlevel", "reorder", "reorderqty", "reorderpoint", "minstock", "minimumstock", "minqty", "minimumqty", "threshold", "alertqty"]),
        "price": ("money", ["price", "rate", "sellingprice", "saleprice", "unitprice", "mrp", "priceinr", "pricers", "sp"]),
    }),
    "expenses": (m.Expense, s.ExpenseIn, {
        "title": ("text", ["title", "expense", "expensename", "description", "details", "particulars", "narration", "name", "item", "purpose", "remarks"]),
        "category": ("text", ["category", "type", "head", "expensetype", "expensehead", "group", "account"]),
        "amount": ("money", ["amount", "amt", "cost", "value", "total", "price", "debit", "amountinr", "amountrs", "paid", "spent"]),
        "date": ("date", ["date", "expensedate", "billdate", "paidon", "day", "transactiondate", "txndate", "invoicedate"]),
    }),
}
DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y",
                "%d-%b-%Y", "%d %b %Y", "%d-%b-%y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d-%B-%Y"]

def norm(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())

def decode(raw: bytes) -> str:
    if raw[:2] == b"PK" or raw[:4] == b"\xd0\xcf\x11\xe0":
        raise HTTPException(415, "This looks like an Excel file. In Excel use File > Save As > CSV, then upload the .csv file.")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")

def read_rows(textdata: str) -> tuple[list[str], list[list[str]]]:
    sample = textdata[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(textdata), dialect))
    rows = [r for r in rows if any(c.strip() for c in r)]  # drop blank lines
    if not rows:
        raise HTTPException(422, "The file is empty.")
    return [h.strip() for h in rows[0]], rows[1:]

def map_columns(headers: list[str], fields: dict) -> dict[str, int]:
    """field -> column index. Exact alias first, then headers that contain an alias (e.g. 'Selling Price (Rs)')."""
    out, used = {}, set()
    normed = [norm(h) for h in headers]
    for exact in (True, False):
        for field, (_, aliases) in fields.items():
            if field in out:
                continue
            for i, h in enumerate(normed):
                if i in used or not h:
                    continue
                if (h in aliases) if exact else any(len(a) > 3 and a in h for a in aliases):
                    out[field] = i; used.add(i)
                    break
    return out

def number(v: str) -> float:
    t = re.sub(r"(?i)(₹|rs\.?|inr|\s|,)", "", v)
    if re.fullmatch(r"\(\d+(\.\d+)?\)", t):
        t = "-" + t[1:-1]
    return float(t)

def parse(kind: str, v: str):
    v = v.strip()
    if v == "":
        return None
    if kind in ("money", "int"):
        try:
            n = number(v)
        except ValueError:
            raise ValueError(f"'{v}' is not a number")
        if kind == "int":
            if n != int(n):
                raise ValueError(f"'{v}' must be a whole number")
            return int(n)
        return round(n, 2)
    if kind == "date":
        for f in DATE_FORMATS:
            try:
                return dt.datetime.strptime(v, f).date()
            except ValueError:
                pass
        if re.fullmatch(r"\d{5}(\.0+)?", v) and 20000 < float(v) < 80000:  # Excel date serial number
            return dt.date(1899, 12, 30) + dt.timedelta(days=int(float(v)))
        raise ValueError(f"'{v}' is not a date (use YYYY-MM-DD or DD/MM/YYYY)")
    if kind == "phone" and re.fullmatch(r"\d+\.0+", v):  # Excel turned the number into 9822011234.0
        v = v.split(".")[0]
    return v

def pretty(e: ValidationError) -> str:
    parts = []
    for x in e.errors():
        field = ".".join(str(p) for p in x["loc"]) or "row"
        parts.append(f"{field}: {x['msg']}")
    return "; ".join(parts)

def key(entity: str, d: dict):
    """What counts as 'the same record' for skipping duplicates."""
    if entity == "products":
        return d["sku"].lower()
    if entity == "expenses":
        return (d["title"].lower(), round(float(d["amount"]), 2), d["date"])
    return (d["name"].lower(), (d.get("phone") or "").lower())

def existing_keys(db, entity, Model, user):
    rows = db.query(Model).filter_by(owner_id=user.id).all()
    if entity == "products":
        return {r.sku.lower(): r for r in rows}
    if entity == "expenses":
        return {(r.title.lower(), round(float(r.amount), 2), r.date): r for r in rows}
    return {(r.name.lower(), (r.phone or "").lower()): r for r in rows}

@router.post("/{entity}")
async def import_csv(entity: str, file: UploadFile = File(...), commit: bool = False,
                     db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    if entity not in SPECS:
        raise HTTPException(404, f"Import supports: {', '.join(SPECS)}")
    Model, Schema, fields = SPECS[entity]
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 5 MB. Split it into smaller files.")
    headers, rows = read_rows(decode(raw))
    if len(rows) > MAX_ROWS:
        raise HTTPException(413, f"File has {len(rows)} rows. The limit is {MAX_ROWS} per upload.")
    cols = map_columns(headers, fields)
    required = [f for f, info in Schema.model_fields.items() if info.is_required() and f in fields]
    missing = [f for f in required if f not in cols]
    mapping = {h: next((f for f, i in cols.items() if i == idx), None) for idx, h in enumerate(headers) if h}
    if missing:
        raise HTTPException(422, f"Could not find a column for: {', '.join(missing)}. "
                                 f"Found columns: {', '.join(h for h in headers if h) or 'none'}. "
                                 "Rename the header row or download the template.")

    known = existing_keys(db, entity, Model, user)
    seen, errors, preview = {}, [], []
    created = updated = skipped = 0
    for n, row in enumerate(rows, start=2):  # row 1 is the header, as in Excel
        data, bad = {}, []
        for f, idx in cols.items():
            try:
                v = parse(fields[f][0], row[idx] if idx < len(row) else "")
            except ValueError as e:
                bad.append(f"{f}: {e}")
                continue
            if v is not None:
                data[f] = v
        if bad:
            errors.append({"row": n, "message": "; ".join(bad)}); continue
        try:
            clean = Schema(**data).model_dump()
        except ValidationError as e:
            errors.append({"row": n, "message": pretty(e)}); continue
        k = key(entity, clean)
        if k in seen:
            if entity == "products":
                errors.append({"row": n, "message": f"SKU {clean['sku']} is repeated (first seen on row {seen[k]})"})
            else:
                skipped += 1
            continue
        seen[k] = n
        action = "create"
        if k in known:
            if entity != "products":
                skipped += 1
                continue
            action = "update"
        if len(preview) < 8:
            preview.append({"row": n, "action": action, **{f: clean[f] for f in fields}})
        if action == "update":
            obj = known[k]
            for f in data:  # only columns that are in the file and filled in
                setattr(obj, f, clean[f])
            updated += 1
        else:
            if commit:
                db.add(Model(**clean, owner_id=user.id))
            created += 1
    if commit:
        safe_commit(db, "Some rows clash with existing records. Nothing was imported.")
    else:
        db.rollback()  # preview only: drop the in-memory updates
    return {"entity": entity, "committed": commit, "total_rows": len(rows), "columns": mapping,
            "created": created, "updated": updated, "skipped": skipped,
            "error_count": len(errors), "errors": errors[:100], "preview": preview}
