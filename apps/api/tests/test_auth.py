from fastapi.testclient import TestClient

def test_me_endpoint_returns_user_info(client: TestClient, auth_headers: dict[str, str]) -> None:
    me = client.get("/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"
    assert me.json()["name"] == "Test User"
    assert me.json()["emailVerified"] is True


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

