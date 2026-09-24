def register(client, email="user@example.com"):
    return client.post("/api/v1/auth/register", json={"name": "User", "email": email, "password": "password123"})


def test_register_duplicate_and_login(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 400
    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"})
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "wrong"}).status_code == 401


def test_me_requires_token(client):
    register(client)
    assert client.get("/api/v1/users/me").status_code == 401
    token = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"}).json()["access_token"]
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200 and response.json()["role"] == "REQUESTER"
