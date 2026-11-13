import datetime as dt

def up(client, h, entity, content, commit=True, name="data.csv"):
    data = content.encode("utf-8-sig") if isinstance(content, str) else content
    return client.post(f"/api/import/{entity}?commit={'true' if commit else 'false'}", headers=h,
                       files={"file": (name, data, "text/csv")})

def test_customers_with_friendly_headers(client, user):
    csv = "Customer Name,Mobile No,City\nAsha Traders,9822011234.0,Pune\nRohan,,Mumbai\n,123,Nowhere\n\n"
    r = up(client, user, "customers", csv)
    j = r.json()
    assert r.status_code == 200, r.text
    assert j["columns"] == {"Customer Name": "name", "Mobile No": "phone", "City": "city"}
    assert j["created"] == 2 and j["error_count"] == 1 and j["errors"][0]["row"] == 4
    rows = client.get("/api/customers", headers=user).json()
    assert {(c["name"], c["phone"]) for c in rows} == {("Asha Traders", "9822011234"), ("Rohan", "")}
    # uploading the same file again does not create duplicates
    assert up(client, user, "customers", csv).json()["skipped"] == 2
    assert len(client.get("/api/customers", headers=user).json()) == 2

def test_preview_saves_nothing(client, user):
    j = up(client, user, "suppliers", "Vendor,Phone,Supplies\nWood Co,111,Teak\n", commit=False).json()
    assert j["committed"] is False and j["created"] == 1 and j["preview"][0]["name"] == "Wood Co"
    assert client.get("/api/suppliers", headers=user).json() == []

def test_products_semicolon_rupees_and_update(client, user):
    client.post("/api/products", headers=user, json={"name": "Chair", "sku": "CH-1", "stock": 1, "reorder_level": 0, "price": 10})
    csv = "Item Name;SKU;Qty;Reorder Level;Selling Price (Rs)\nChair;CH-1;7;2;\"₹1,250.50\"\nTable;TB-1;3;1;4500\nBad;TB-2;2.5;0;10\nDup;TB-1;1;1;1\n"
    j = up(client, user, "products", csv).json()
    assert j["created"] == 1 and j["updated"] == 1 and j["error_count"] == 2, j
    assert "whole number" in j["errors"][0]["message"] and "repeated" in j["errors"][1]["message"]
    p = {x["sku"]: x for x in client.get("/api/products", headers=user).json()}
    assert p["CH-1"]["stock"] == 7 and p["CH-1"]["price"] == 1250.5 and p["TB-1"]["price"] == 4500

def test_preview_of_update_does_not_change_product(client, user):
    client.post("/api/products", headers=user, json={"name": "Chair", "sku": "CH-1", "stock": 1, "reorder_level": 0, "price": 10})
    j = up(client, user, "products", "name,sku,stock\nChair,CH-1,99\n", commit=False).json()
    assert j["updated"] == 1 and j["preview"][0]["action"] == "update"
    assert client.get("/api/products", headers=user).json()[0]["stock"] == 1

def test_expenses_dates_and_amounts(client, user):
    csv = ("Particulars,Head,Amount,Date\n"
           "Rent,Office,\"Rs. 12,000\",05/11/2026\n"
           "Tea,,150,2026-11-02\n"
           "Wood,Supplies,8000,46000\n"
           "Refund,,-50,2026-11-01\n"
           "Oops,,100,31/31/2026\n")
    j = up(client, user, "expenses", csv).json()
    assert j["created"] == 3 and j["error_count"] == 2, j
    rows = {e["title"]: e for e in client.get("/api/expenses", headers=user).json()}
    assert rows["Rent"]["amount"] == 12000 and rows["Rent"]["date"] == "2026-11-05"  # day first, Indian style
    assert rows["Tea"]["category"] == "General"
    assert rows["Wood"]["date"] == (dt.date(1899, 12, 30) + dt.timedelta(days=46000)).isoformat()

def test_cp1252_and_tabs(client, user):
    raw = "Name\tCity\nCaf\xe9 Rao\tGoa\n".encode("cp1252")
    j = up(client, user, "customers", raw).json()
    assert j["created"] == 1
    assert client.get("/api/customers", headers=user).json()[0]["name"] == "Café Rao"

def test_bad_files(client, user):
    r = up(client, user, "customers", "Phone,City\n1,Pune\n")
    assert r.status_code == 422 and "name" in r.json()["detail"]
    assert up(client, user, "customers", b"PK\x03\x04xlsxdata", name="a.xlsx").status_code == 415
    assert up(client, user, "customers", "").status_code == 422
    assert up(client, user, "orders", "a\n1\n").status_code == 404
    assert client.post("/api/import/customers", files={"file": ("a.csv", b"name\nx\n")}).status_code == 401

def test_import_is_per_account(client, user, other):
    up(client, user, "customers", "name\nOnly Mine\n")
    assert client.get("/api/customers", headers=other).json() == []
    assert up(client, other, "customers", "name\nOnly Mine\n").json()["created"] == 1
