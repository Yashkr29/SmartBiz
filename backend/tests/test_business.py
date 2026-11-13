def mk(client, h, path, body, code=201):
    r = client.post(f"/api/{path}", json=body, headers=h)
    assert r.status_code == code, r.text
    return r.json()

def setup_shop(client, h):
    c = mk(client, h, "customers", {"name": "Asha Traders", "phone": "98220", "city": "Pune"})
    p = mk(client, h, "products", {"name": "Chair", "sku": "CH-1", "stock": 5, "reorder_level": 2, "price": 1000})
    return c, p

def test_new_user_has_empty_dashboard(client, user):
    d = client.get("/api/dashboard", headers=user).json()
    assert d["total_sales"] == 0 and d["active_orders"] == 0 and d["low_stock"] == [] and d["expenses"] == 0
    assert d["counts"] == {"orders": 0, "customers": 0, "products": 0}
    for path in ("customers", "products", "suppliers", "expenses", "orders"):
        assert client.get(f"/api/{path}", headers=user).json() == []

def test_accounts_are_isolated(client, user, other):
    c, p = setup_shop(client, user)
    o = mk(client, user, "orders", {"customer_id": c["id"], "items": [{"product_id": p["id"], "qty": 1}]})
    mk(client, user, "expenses", {"title": "Rent", "amount": 500})
    # the second account sees none of the first account's data
    for path in ("customers", "products", "expenses", "orders"):
        assert client.get(f"/api/{path}", headers=other).json() == []
    assert client.get("/api/dashboard", headers=other).json()["total_sales"] == 0
    # and cannot read, change or delete it
    assert client.get(f"/api/orders/{o['id']}", headers=other).status_code == 404
    assert client.put(f"/api/customers/{c['id']}", json={"name": "Hacked"}, headers=other).status_code == 404
    assert client.delete(f"/api/products/{p['id']}", headers=other).status_code == 404
    assert client.post(f"/api/orders/{o['id']}/payments", json={"amount": 1}, headers=other).status_code == 404
    assert client.post(f"/api/orders/{o['id']}/advance", headers=other).status_code == 404
    assert client.delete(f"/api/orders/{o['id']}", headers=other).status_code == 404
    # nor build an order from someone else's customer or product
    mine = mk(client, other, "customers", {"name": "Mine"})
    mk(client, other, "orders", {"customer_id": c["id"], "items": [{"product_id": p["id"], "qty": 1}]}, 404)
    mk(client, other, "orders", {"customer_id": mine["id"], "items": [{"product_id": p["id"], "qty": 1}]}, 404)
    assert client.get("/api/products", headers=user).json()[0]["stock"] == 4

def test_sku_unique_per_account(client, user, other):
    body = {"name": "Chair", "sku": "CH-1", "stock": 1, "reorder_level": 0, "price": 10}
    mk(client, user, "products", body)
    mk(client, user, "products", body, 409)
    mk(client, other, "products", body)  # another business may use the same SKU

def test_validation(client, user):
    mk(client, user, "products", {"name": "X", "sku": "S", "stock": -1, "reorder_level": 0, "price": 1}, 422)
    mk(client, user, "customers", {"name": "x" * 121}, 422)
    mk(client, user, "expenses", {"title": "Bad", "amount": 0}, 422)
    mk(client, user, "expenses", {"title": "  ", "amount": 5}, 422)

def test_update_and_search(client, user):
    c = mk(client, user, "customers", {"name": "Rohan", "city": "Mumbai"})
    mk(client, user, "customers", {"name": "Asha", "city": "Pune"})
    r = client.put(f"/api/customers/{c['id']}", json={"name": "Rohan Interiors", "city": "Mumbai"}, headers=user)
    assert r.status_code == 200 and r.json()["name"] == "Rohan Interiors"
    assert [x["name"] for x in client.get("/api/customers?q=pune", headers=user).json()] == ["Asha"]
    assert client.get("/api/customers?q=city", headers=user).json() == []  # field names are not searched

def test_order_lifecycle(client, user):
    c, p = setup_shop(client, user)
    mk(client, user, "orders", {"customer_id": c["id"], "items": [{"product_id": p["id"], "qty": 6}]}, 422)  # oversell
    mk(client, user, "orders", {"customer_id": c["id"], "items": [{"product_id": p["id"], "qty": 2}], "advance": 5000}, 422)
    o = mk(client, user, "orders", {"customer_id": c["id"], "items": [{"product_id": p["id"], "qty": 2}, {"product_id": p["id"], "qty": 1}], "advance": 500})
    assert o["total"] == 3000 and o["paid"] == 500 and o["pending"] == 2500 and o["items"][0]["qty"] == 3
    assert client.get("/api/products", headers=user).json()[0]["stock"] == 2
    assert client.post(f"/api/orders/{o['id']}/payments", json={"amount": 2600}, headers=user).status_code == 422
    r = client.post(f"/api/orders/{o['id']}/payments", json={"amount": 2500, "note": "UPI"}, headers=user)
    assert r.json()["pending"] == 0
    assert client.get("/api/customers", headers=user).json()[0]["due"] == 0
    for stage in range(1, 5):
        assert client.post(f"/api/orders/{o['id']}/advance", headers=user).json()["stage"] == stage
    assert client.post(f"/api/orders/{o['id']}/advance", headers=user).status_code == 409
    assert client.delete(f"/api/orders/{o['id']}", headers=user).status_code == 204
    assert client.get("/api/products", headers=user).json()[0]["stock"] == 2  # delivered: stock is not returned

def test_delete_undelivered_order_returns_stock(client, user):
    c, p = setup_shop(client, user)
    o = mk(client, user, "orders", {"customer_id": c["id"], "items": [{"product_id": p["id"], "qty": 3}]})
    assert client.delete(f"/api/customers/{c['id']}", headers=user).status_code == 409  # still used by an order
    assert client.delete(f"/api/orders/{o['id']}", headers=user).status_code == 204
    assert client.get("/api/products", headers=user).json()[0]["stock"] == 5
    assert client.delete(f"/api/customers/{c['id']}", headers=user).status_code == 204

def test_dashboard_numbers(client, user):
    c, p = setup_shop(client, user)
    mk(client, user, "orders", {"customer_id": c["id"], "items": [{"product_id": p["id"], "qty": 4}], "advance": 1000})
    mk(client, user, "expenses", {"title": "Wood", "amount": 1500.5})
    d = client.get("/api/dashboard", headers=user).json()
    assert d["total_sales"] == 4000 and d["pending_payments"] == 3000 and d["expenses"] == 1500.5
    assert d["estimated_profit"] == 2499.5 and d["active_orders"] == 1
    assert d["low_stock"] == [{"id": p["id"], "name": "Chair", "stock": 1}]
    assert d["weekly_orders"][-1]["v"] == 1 and len(d["weekly_orders"]) == 7
