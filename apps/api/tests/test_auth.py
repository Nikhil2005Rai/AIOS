from fastapi.testclient import TestClient


def test_register_and_login_flow(client: TestClient) -> None:
    # 1. Register new user
    reg = client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "password123", "name": "New User"},
    )
    assert reg.status_code == 200, reg.text
    data = reg.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["name"] == "New User"

    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check /auth/me with new token
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "newuser@example.com"

    # 3. Login with credentials
    login = client.post(
        "/auth/login",
        json={"email": "newuser@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


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


def test_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid bearer token"
