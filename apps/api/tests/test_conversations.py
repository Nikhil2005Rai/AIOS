from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps_providers import get_embedding_provider, get_llm_provider, get_retrieval_repository
from app.domain.entities import RetrievedChunk
from app.infrastructure.models import ToolCallModel
from app.main import app
from app.providers.base import LLMGenerationError, LLMMessage, LLMResponse, LLMToolCall, ToolSchema


class ToolCallingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(content="ROUTE: research")
        if self.calls == 2:
            return LLMResponse(content="", tool_call=LLMToolCall(name="current_time", arguments={}))
        return LLMResponse(content="The current time has been checked by research.")


class KnowledgeRoutingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(content="ROUTE: knowledge")
        context = messages[0].content
        if "alpha beta gamma" in context:
            return LLMResponse(content="Grounded answer from uploaded notes.")
        return LLMResponse(content="No grounded context found.")


class FailingEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("Gemini returned 3072 embedding dimensions, expected 768.")


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]


class FakeRetrievalRepository:
    def search(self, user_id: str, embedding: list[float], limit: int = 4) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                id="chunk-1",
                document_id="document-1",
                content="alpha beta gamma",
                score=0.01,
            )
        ]


def test_create_list_send_message_and_persist_assistant_reply(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create = client.post("/conversations", headers=auth_headers, json={"title": "Planner session"})
    assert create.status_code == 201
    conversation_id = create.json()["id"]

    conversations = client.get("/conversations", headers=auth_headers)
    assert conversations.status_code == 200
    assert conversations.json()[0]["title"] == "Planner session"

    send = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"content": "Hello planner"},
    )
    assert send.status_code == 201
    assert send.json()["assistant_message"]["content"] == "Fake assistant reply"

    messages = client.get(f"/conversations/{conversation_id}/messages", headers=auth_headers)
    assert messages.status_code == 200
    assert [message["role"] for message in messages.json()] == ["user", "assistant"]
    assert messages.json()[1]["content"] == "Fake assistant reply"


def test_send_message_logs_tool_call_when_provider_requests_tool(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    provider = ToolCallingProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider

    create = client.post("/conversations", headers=auth_headers, json={"title": "Tool session"})
    conversation_id = create.json()["id"]

    send = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"content": "What time is it?"},
    )

    assert send.status_code == 201
    assistant_message = send.json()["assistant_message"]
    assert assistant_message["tool_name"] == "current_time"

    tool_call = db_session.scalar(select(ToolCallModel).where(ToolCallModel.tool_name == "current_time"))
    assert tool_call is not None
    assert tool_call.conversation_id == conversation_id
    assert tool_call.message_id == assistant_message["id"]
    assert tool_call.agent_name == "research"
    assert tool_call.arguments == "{}"
    assert "Current local time is" in tool_call.output


def test_send_message_returns_502_when_knowledge_embedding_fails(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    app.dependency_overrides[get_llm_provider] = lambda: KnowledgeRoutingProvider()
    app.dependency_overrides[get_embedding_provider] = lambda: FailingEmbeddingProvider()

    create = client.post("/conversations", headers=auth_headers, json={"title": "Knowledge session"})
    conversation_id = create.json()["id"]

    send = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"content": "Using my uploaded knowledge, answer this."},
    )

    assert send.status_code == 502
    assert "Embedding provider failed" in send.json()["detail"]
    assert "expected 768" in send.json()["detail"]


def test_upload_document_then_knowledge_question_returns_grounded_answer(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    app.dependency_overrides[get_embedding_provider] = lambda: FakeEmbeddingProvider()

    upload = client.post(
        "/documents",
        headers=auth_headers,
        json={"title": "Notes", "content": "alpha beta gamma"},
    )
    assert upload.status_code == 201

    app.dependency_overrides[get_llm_provider] = lambda: KnowledgeRoutingProvider()
    app.dependency_overrides[get_retrieval_repository] = lambda: FakeRetrievalRepository()

    create = client.post("/conversations", headers=auth_headers, json={"title": "Knowledge session"})
    conversation_id = create.json()["id"]
    send = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"content": "Using my uploaded knowledge, answer this."},
    )

    assert send.status_code == 201
    assert send.json()["assistant_message"]["content"] == "Grounded answer from uploaded notes."


class GenerationFailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(content="ROUTE: research")
        raise LLMGenerationError("Gemini stopped with finishReason=MAX_TOKENS before producing an answer.")


def test_send_message_returns_502_when_generation_fails(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    app.dependency_overrides[get_llm_provider] = lambda: GenerationFailingProvider()

    create = client.post("/conversations", headers=auth_headers, json={"title": "Research session"})
    conversation_id = create.json()["id"]

    send = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"content": "What is the time?"},
    )

    assert send.status_code == 502
    assert "LLM provider failed" in send.json()["detail"]
    assert "MAX_TOKENS" in send.json()["detail"]

