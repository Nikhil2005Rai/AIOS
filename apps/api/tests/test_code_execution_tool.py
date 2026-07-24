from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.tools.code_execution import CodeExecutionTool


def test_code_execution_success() -> None:
    tool = CodeExecutionTool()
    arguments = {"language": "python", "code": "print('hello')", "stdin": ""}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "run": {
            "stdout": "hello\n",
            "stderr": "",
            "code": 0,
        }
    }

    with patch("httpx.post", return_value=mock_response) as mock_post:
        result = tool.run(arguments)
        mock_post.assert_called_once()
        assert "Exit code: 0" in result
        assert "stdout:\nhello\n" in result


def test_code_execution_unsupported_language() -> None:
    tool = CodeExecutionTool()
    arguments = {"language": "ruby", "code": "puts 'hello'"}

    with patch("httpx.post") as mock_post:
        result = tool.run(arguments)
        mock_post.assert_not_called()
        assert "Error: unsupported language 'ruby'" in result


def test_code_execution_timeout() -> None:
    tool = CodeExecutionTool()
    arguments = {"language": "python", "code": "import time; time.sleep(100)"}

    with patch("httpx.post", side_effect=httpx.TimeoutException("Timeout")):
        result = tool.run(arguments)
        assert "Error: code execution timed out" in result


def test_code_execution_http_error() -> None:
    tool = CodeExecutionTool()
    arguments = {"language": "python", "code": "print('test')"}

    mock_request = httpx.Request("POST", "https://emkc.org/api/v2/piston/execute")
    mock_response = httpx.Response(status_code=401, text="Unauthorized access", request=mock_request)
    http_err = httpx.HTTPStatusError("401 Client Error", request=mock_request, response=mock_response)

    with patch("httpx.post", side_effect=http_err):
        result = tool.run(arguments)
        assert "Error: execution service returned 401" in result
