from collections.abc import Callable
from dataclasses import dataclass

from app.agents.knowledge import KnowledgeAgent
from app.agents.research import ResearchAgent
from app.providers.base import LLMProvider
from app.providers.embeddings.base import EmbeddingProvider
from app.retrieval.repository import RetrievalRepository
from app.tools.registry import ToolRegistry


@dataclass(slots=True)
class AgentBuildContext:
    llm_provider: LLMProvider
    tools: ToolRegistry
    embedding_provider: EmbeddingProvider | None = None
    retrieval_repository: RetrievalRepository | None = None
    user_id: str | None = None


AgentFactory = Callable[[AgentBuildContext], object]


class AgentRegistry:
    def __init__(self, factories: dict[str, AgentFactory]) -> None:
        self._factories = factories

    def build(self, name: str, context: AgentBuildContext) -> object:
        factory = self._factories.get(name)
        if factory is None:
            supported = ", ".join(sorted(self._factories))
            raise ValueError(f"Unsupported agent {name!r}. Supported agents: {supported}.")
        return factory(context)

    def names(self) -> list[str]:
        return sorted(self._factories)


def build_agent_registry() -> AgentRegistry:
    return AgentRegistry(
        factories={
            ResearchAgent.name: lambda context: ResearchAgent(context.llm_provider, context.tools),
            KnowledgeAgent.name: lambda context: KnowledgeAgent(
                llm_provider=context.llm_provider,
                embedding_provider=context.embedding_provider,
                retrieval_repository=context.retrieval_repository,
                user_id=context.user_id,
            ),
        }
    )
