from conftest import signup

def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"name": "Asha", "email": "Asha@Shop.com", "password": "secret123"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "admin"
    assert client.post("/api/auth/register", json={"name": "X", "email": "asha@shop.com", "password": "secret123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "asha@shop.com", "password": "wrongpass"}).status_code == 401
    tok = client.post("/api/auth/login", json={"email": "ASHA@shop.com", "password": "secret123"}).json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.json()["email"] == "asha@shop.com"

def test_every_signup_is_owner(client):
    for _ in range(3):
        h = signup(client)
        assert client.get("/api/auth/me", headers=h).json()["role"] == "admin"

def test_missing_or_bad_token_is_401(client):
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/dashboard", headers={"Authorization": "Bearer nope"}).status_code == 401

def test_long_unicode_password(client):
    pw = "अ" * 60  # 180 bytes; bcrypt>=5 refuses more than 72 bytes
    r = client.post("/api/auth/register", json={"name": "U", "email": "uni@test.com", "password": pw})
    assert r.status_code == 201
    assert client.post("/api/auth/login", json={"email": "uni@test.com", "password": pw}).status_code == 200

def test_blank_name_rejected(client):
    r = client.post("/api/auth/register", json={"name": "   ", "email": "blank@test.com", "password": "secret123"})
    assert r.status_code == 422
