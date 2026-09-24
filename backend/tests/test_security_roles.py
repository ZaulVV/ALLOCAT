from backend.tests.test_auth import register


def test_requester_cannot_manage_resources(client):
    register(client)
    token = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/resources", headers=headers, json={"name": "Laptop", "category": "material"}).status_code == 403
    assert client.get("/api/v1/logs", headers=headers).status_code == 403
