from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.planner import PlannerAgent, PlannerResult
from app.agents.registry import AgentBuildContext, AgentRegistry
from app.providers.base import LLMMessage, LLMProvider
from app.providers.embeddings.base import EmbeddingProvider
from app.retrieval.repository import RetrievalRepository
from app.tools.registry import ToolRegistry


class AgentGraphState(TypedDict, total=False):
    user_input: str
    history: list[LLMMessage]
    route: str
    answer: str
    tool_name: str | None
    tool_arguments: dict | None
    tool_output: str | None
    agent_name: str | None
    retrieval_query: str | None
    retrieval_chunk_ids: list[str] | None
    retrieval_scores: list[float] | None


class MultiAgentGraph(PlannerAgent):
    def __init__(
        self,
        llm_provider: LLMProvider,
        tools: ToolRegistry,
        agents: AgentRegistry,
        embedding_provider: EmbeddingProvider | None = None,
        retrieval_repository: RetrievalRepository | None = None,
        user_id: str | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.tools = tools
        self.agents = agents
        self.embedding_provider = embedding_provider
        self.retrieval_repository = retrieval_repository
        self.user_id = user_id
        self.graph = self._build_graph()

    def run(self, user_input: str, history: list[LLMMessage] | None = None) -> PlannerResult:
        final_state = self.graph.invoke({"user_input": user_input, "history": history or []})
        return PlannerResult(
            answer=final_state.get("answer", ""),
            tool_name=final_state.get("tool_name"),
            tool_arguments=final_state.get("tool_arguments"),
            tool_output=final_state.get("tool_output"),
            agent_name=final_state.get("agent_name"),
            retrieval_query=final_state.get("retrieval_query"),
            retrieval_chunk_ids=final_state.get("retrieval_chunk_ids"),
            retrieval_scores=final_state.get("retrieval_scores"),
        )

    def _build_graph(self):
        graph = StateGraph(AgentGraphState)
        graph.add_node("planner", self._planner_node)
        graph.add_node("research", self._research_node)
        graph.add_node("knowledge", self._knowledge_node)
        graph.set_entry_point("planner")
        graph.add_conditional_edges(
            "planner",
            self._route_from_planner,
            {"research": "research", "knowledge": "knowledge", "end": END},
        )
        graph.add_edge("research", END)
        graph.add_edge("knowledge", END)
        return graph.compile()

    def _planner_node(self, state: AgentGraphState) -> AgentGraphState:
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "You are the Planner agent in an AI OS monolith. Decide whether the user's request "
                    "needs a specialist. If it asks about the user's uploaded/pasted knowledge, documents, "
                    "notes, or saved context, respond exactly with 'ROUTE: knowledge'. If it needs research, "
                    "current facts, investigation, or tool-supported lookup, respond exactly with "
                    "'ROUTE: research'. Otherwise answer directly and prefix the answer with 'ANSWER:'."
                ),
            ),
            *state.get("history", [])[-12:],
            LLMMessage(role="user", content=state["user_input"]),
        ]
        response = self.llm_provider.generate(messages)
        content = response.content.strip()
        if content.lower().startswith("route: knowledge"):
            return {"route": "knowledge"}
        if content.lower().startswith("route: research"):
            return {"route": "research"}
        if content.lower().startswith("answer:"):
            content = content.split(":", 1)[1].strip()
        return {"route": "end", "answer": content, "agent_name": "planner"}

    @staticmethod
    def _route_from_planner(state: AgentGraphState) -> Literal["research", "knowledge", "end"]:
        route = state.get("route")
        if route == "research":
            return "research"
        if route == "knowledge":
            return "knowledge"
        return "end"

    def _research_node(self, state: AgentGraphState) -> AgentGraphState:
        research_agent = self.agents.build("research", self._agent_context())
        result = research_agent.run(state["user_input"], history=state.get("history", []))
        return {
            "answer": result.answer,
            "tool_name": result.tool_name,
            "tool_arguments": result.tool_arguments,
            "tool_output": result.tool_output,
            "agent_name": result.agent_name or "research",
        }

    def _knowledge_node(self, state: AgentGraphState) -> AgentGraphState:
        knowledge_agent = self.agents.build("knowledge", self._agent_context())
        result = knowledge_agent.run(state["user_input"], history=state.get("history", []))
        return {
            "answer": result.answer,
            "agent_name": result.agent_name or "knowledge",
            "retrieval_query": result.retrieval_query,
            "retrieval_chunk_ids": result.retrieval_chunk_ids,
            "retrieval_scores": result.retrieval_scores,
        }

    def _agent_context(self) -> AgentBuildContext:
        return AgentBuildContext(
            llm_provider=self.llm_provider,
            tools=self.tools,
            embedding_provider=self.embedding_provider,
            retrieval_repository=self.retrieval_repository,
            user_id=self.user_id,
        )
