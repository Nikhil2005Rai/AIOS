import os

from app.core.config import settings


def configure_langsmith() -> None:
    """Sets the standard LANGCHAIN_* env vars that both LangGraph's built-in
    instrumentation and the langsmith @traceable decorator read at call time.
    No-op (tracing disabled) unless both a tracing flag and an API key are set."""
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
