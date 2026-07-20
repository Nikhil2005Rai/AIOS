import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimiter


class FakeRateLimitRedisCache:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key: str) -> int | None:
        current = self.counts.get(key, 0) + 1
        self.counts[key] = current
        return current

    def expire(self, key: str, ttl_seconds: int) -> None:
        self.ttls[key] = ttl_seconds

    def reset_key(self, key: str) -> None:
        self.counts.pop(key, None)
        self.ttls.pop(key, None)


class FailingIncrRedisCache:
    def incr(self, key: str) -> int | None:
        return None

    def expire(self, key: str, ttl_seconds: int) -> None:
        pass


def test_rate_limiter_check_unit() -> None:
    cache = FakeRateLimitRedisCache()
    limiter = RateLimiter(cache)

    limit = 3
    window = 60
    key = "test:bucket:123"

    # First 3 calls should return True
    assert limiter.check(key, limit, window) is True
    assert limiter.check(key, limit, window) is True
    assert limiter.check(key, limit, window) is True
    assert cache.ttls.get(key) == window

    # 4th call should return False (exceeded)
    assert limiter.check(key, limit, window) is False

    # Simulate key expiry / reset
    cache.reset_key(key)

    # Calling again after expiry returns True
    assert limiter.check(key, limit, window) is True


def test_rate_limiter_fail_open_unit() -> None:
    cache = FailingIncrRedisCache()
    limiter = RateLimiter(cache)

    # When incr returns None, check returns True (fail open)
    assert limiter.check("test:bucket:err", limit=2, window_seconds=60) is True


def test_rate_limit_register_ip_integration(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_cache = FakeRateLimitRedisCache()
    monkeypatch.setattr("app.api.rate_limit_dependencies.build_redis_cache", lambda: fake_cache)

    # /auth/register limit is 3 requests per 3600s
    for i in range(3):
        res = client.post("/auth/register", json={"email": f"rate{i}@example.com", "password": "password123"})
        assert res.status_code == 201

    # 4th request should return 429
    res_4th = client.post("/auth/register", json={"email": "rate_over@example.com", "password": "password123"})
    assert res_4th.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert res_4th.json()["detail"] == "Rate limit exceeded. Try again in a moment."


def test_rate_limit_send_message_user_integration(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_cache = FakeRateLimitRedisCache()
    monkeypatch.setattr("app.api.rate_limit_dependencies.build_redis_cache", lambda: fake_cache)

    from app.jobs.entities import JobStatus

    class FakeJob:
        id = "fake-job-id"
        status = JobStatus.QUEUED

    class FakeJobQueue:
        def enqueue(self, *args, **kwargs):
            return FakeJob()

    monkeypatch.setattr("app.api.routes.conversations.build_job_queue", lambda: FakeJobQueue())

    conv_res = client.post("/conversations", headers=auth_headers, json={"title": "Rate Limit Chat"})
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # send_message limit is 20 requests per 60s
    for i in range(20):
        res = client.post(
            f"/conversations/{conv_id}/messages",
            headers=auth_headers,
            json={"content": f"msg {i}"},
        )
        assert res.status_code == 202

    # 21st request should return 429
    res_over = client.post(
        f"/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "msg 21"},
    )
    assert res_over.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert res_over.json()["detail"] == "Rate limit exceeded. Try again in a moment."
