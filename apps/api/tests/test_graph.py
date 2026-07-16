from app.agents.graph import MultiAgentGraph
from app.agents.registry import build_agent_registry
from app.domain.entities import RetrievedChunk
from app.providers.base import LLMMessage, LLMResponse, ToolSchema
from app.tools.registry import ToolRegistry


class ScriptedGraphProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[list[LLMMessage], list[ToolSchema] | None]] = []

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        self.calls.append((messages, tools))
        return self.responses.pop(0)


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]


class FakeRetrievalRepository:
    def search(self, user_id: str, embedding: list[float], limit: int = 4) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                id="chunk-1",
                document_id="document-1",
                content="uploaded project notes",
                score=0.01,
            )
        ]


def test_graph_planner_answers_directly() -> None:
    provider = ScriptedGraphProvider([LLMResponse(content="ANSWER: Direct graph answer")])
    graph = MultiAgentGraph(llm_provider=provider, tools=ToolRegistry([]), agents=build_agent_registry())

    result = graph.run("Say hello")

    assert result.answer == "Direct graph answer"
    assert result.agent_name == "planner"
    assert len(provider.calls) == 1


def test_graph_routes_to_research_agent() -> None:
    provider = ScriptedGraphProvider(
        [
            LLMResponse(content="ROUTE: research"),
            LLMResponse(content="Research answer"),
        ]
    )
    graph = MultiAgentGraph(llm_provider=provider, tools=ToolRegistry([]), agents=build_agent_registry())

    result = graph.run("Research this")

    assert result.answer == "Research answer"
    assert result.agent_name == "research"
    assert len(provider.calls) == 2


def test_graph_routes_to_knowledge_agent() -> None:
    provider = ScriptedGraphProvider(
        [
            LLMResponse(content="ROUTE: knowledge"),
            LLMResponse(content="Grounded knowledge answer"),
        ]
    )
    graph = MultiAgentGraph(
        llm_provider=provider,
        tools=ToolRegistry([]),
        agents=build_agent_registry(),
        embedding_provider=FakeEmbeddingProvider(),
        retrieval_repository=FakeRetrievalRepository(),
        user_id="user-1",
    )

    result = graph.run("Use my uploaded knowledge")

    assert result.answer == "Grounded knowledge answer"
    assert result.agent_name == "knowledge"
    assert result.retrieval_chunk_ids == ["chunk-1"]
    assert len(provider.calls) == 2
