import json
import logging
import sys

from fastapi.testclient import TestClient

from app.core.logging_config import JSONFormatter, RequestIdFilter, request_id_var


def test_json_formatter_valid_json() -> None:
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    
    output = formatter.format(record)
    parsed = json.loads(output)
    
    assert "timestamp" in parsed
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test message"
    assert "request_id" not in parsed
    assert "job_id" not in parsed
    assert "user_id" not in parsed
    assert "exception" not in parsed


def test_json_formatter_custom_attributes() -> None:
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.DEBUG,
        pathname="test.py",
        lineno=10,
        msg="Test custom attrs",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"
    record.job_id = "job-456"
    record.user_id = "user-789"
    
    output = formatter.format(record)
    parsed = json.loads(output)
    
    assert parsed["request_id"] == "req-123"
    assert parsed["job_id"] == "job-456"
    assert parsed["user_id"] == "user-789"


def test_json_formatter_exception() -> None:
    formatter = JSONFormatter()
    try:
        1 / 0
    except ZeroDivisionError:
        exc_info = sys.exc_info()
        
    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=10,
        msg="Error occurred",
        args=(),
        exc_info=exc_info,
    )
    
    output = formatter.format(record)
    parsed = json.loads(output)
    
    assert parsed["level"] == "ERROR"
    assert "ZeroDivisionError" in parsed["exception"]


def test_request_id_filter() -> None:
    filter_ = RequestIdFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    
    token = request_id_var.set("test-request-id")
    try:
        assert filter_.filter(record) is True
        assert record.request_id == "test-request-id"
    finally:
        request_id_var.reset(token)


def test_middleware_generates_request_id(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


def test_middleware_echoes_request_id(client: TestClient) -> None:
    custom_id = "custom-id-999"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] == custom_id
