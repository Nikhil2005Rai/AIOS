from fastapi.testclient import TestClient


def test_register_duplicate_login_bad_password_and_me(client: TestClient) -> None:
    register = client.post("/auth/register", json={"email": "alice@example.com", "password": "password123"})
    assert register.status_code == 201
    token = register.json()["access_token"]

    duplicate = client.post("/auth/register", json={"email": "alice@example.com", "password": "password123"})
    assert duplicate.status_code == 409

    login = client.post("/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert login.status_code == 200
    assert login.json()["access_token"]

    bad_password = client.post("/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert bad_password.status_code == 401

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_me_returns_preferred_provider_after_saving_key(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    before = client.get("/auth/me", headers=auth_headers)
    assert before.status_code == 200
    assert before.json()["preferred_provider"] is None

    save = client.post(
        "/users/me/api-keys",
        headers=auth_headers,
        json={"provider": "groq", "api_key": "user-key"},
    )
    assert save.status_code == 200

    after = client.get("/auth/me", headers=auth_headers)
    assert after.status_code == 200
    assert after.json()["preferred_provider"] == "groq"

