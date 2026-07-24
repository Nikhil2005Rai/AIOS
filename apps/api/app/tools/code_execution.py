import httpx

from app.tools.base import ToolResult

PISTON_API_URL = "https://emkc.org/api/v2/piston"

SUPPORTED_LANGUAGES = {
    "python": "3.10.0",
    "javascript": "18.15.0",
    "typescript": "5.0.3",
    "bash": "5.2.0",
}


class CodeExecutionTool:
    name = "execute_code"
    description = (
        "Executes a code snippet in a sandboxed environment and returns stdout, stderr, "
        "and exit code. Supported languages: " + ", ".join(SUPPORTED_LANGUAGES) + ". "
        "Use this to verify code actually works before presenting it as a final answer."
    )
    parameters = {
        "type": "object",
        "properties": {
            "language": {"type": "string", "enum": list(SUPPORTED_LANGUAGES.keys())},
            "code": {"type": "string", "description": "The full source code to execute."},
            "stdin": {"type": "string", "description": "Optional stdin input.", "default": ""},
        },
        "required": ["language", "code"],
    }

    def execute(self, arguments: dict) -> ToolResult:
        result_text = self.run(arguments)
        return ToolResult(content=result_text)

    def run(self, arguments: dict) -> str:
        language = arguments.get("language", "")
        code = arguments.get("code", "")
        stdin = arguments.get("stdin", "")

        if language not in SUPPORTED_LANGUAGES:
            return f"Error: unsupported language '{language}'. Supported: {', '.join(SUPPORTED_LANGUAGES)}"

        payload = {
            "language": language,
            "version": SUPPORTED_LANGUAGES[language],
            "files": [{"content": code}],
            "stdin": stdin,
        }
        try:
            response = httpx.post(f"{PISTON_API_URL}/execute", json=payload, timeout=15)
            response.raise_for_status()
        except httpx.TimeoutException:
            return "Error: code execution timed out (Piston sandbox took too long to respond)."
        except httpx.HTTPStatusError as exc:
            return f"Error: execution service returned {exc.response.status_code} — {exc.response.text[:300]}"
        except httpx.HTTPError as exc:
            return f"Error: could not reach code execution service ({exc})."

        data = response.json()
        run_result = data.get("run", {})
        stdout = run_result.get("stdout", "")
        stderr = run_result.get("stderr", "")
        exit_code = run_result.get("code")

        parts = [f"Exit code: {exit_code}"]
        if stdout:
            parts.append(f"stdout:\n{stdout}")
        if stderr:
            parts.append(f"stderr:\n{stderr}")
        return "\n\n".join(parts)
