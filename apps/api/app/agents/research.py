from app.agents.planner import PlannerResult
from app.providers.base import LLMMessage, LLMProvider
from app.tools.registry import ToolRegistry


class ResearchAgent:
    name = "research"

    def __init__(self, llm_provider: LLMProvider, tools: ToolRegistry) -> None:
        self.llm_provider = llm_provider
        self.tools = tools

    def run(self, user_input: str, history: list[LLMMessage] | None = None) -> PlannerResult:
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "You are the Research agent in an AI OS monolith. Investigate the user's request, "
                    "use an available tool only when it materially improves the answer, and return a "
                    "concise research-style response."
                ),
            )
        ]
        if history:
            messages.extend(history[-12:])
        messages.append(LLMMessage(role="user", content=user_input))

        first_response = self.llm_provider.generate(messages, tools=self.tools.schemas())
        if first_response.tool_call is None:
            return PlannerResult(answer=first_response.content, agent_name=self.name)

        tool = self.tools.get(first_response.tool_call.name)
        if tool is None:
            return PlannerResult(
                answer=f"Requested research tool is not available: {first_response.tool_call.name}",
                agent_name=self.name,
            )

        tool_result = tool.execute(first_response.tool_call.arguments)
        final_response = self.llm_provider.generate(
            [
                *messages,
                LLMMessage(
                    role="assistant",
                    content=(
                        f"I requested tool {first_response.tool_call.name} with arguments "
                        f"{first_response.tool_call.arguments}."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"Tool {first_response.tool_call.name} returned: {tool_result.content}\n"
                        "Use this tool result to answer the original research request."
                    ),
                ),
            ]
        )
        return PlannerResult(
            answer=final_response.content,
            tool_name=first_response.tool_call.name,
            tool_arguments=first_response.tool_call.arguments,
            tool_output=tool_result.content,
            agent_name=self.name,
        )
