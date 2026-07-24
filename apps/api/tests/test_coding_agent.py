from app.agents.coding import CodingAgent
from app.providers.base import LLMMessage, LLMProvider, LLMResponse, LLMToolCall, ToolSchema
from app.tools.code_execution import CodeExecutionTool
from app.tools.registry import ToolRegistry


class ScriptedLLMProvider(LLMProvider):
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.call_count = 0

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        res = self.responses[self.call_count]
        self.call_count += 1
        return res


def test_coding_agent_direct_answer() -> None:
    llm = ScriptedLLMProvider([LLMResponse(content="Here is a simple python script: print('hello')")])
    tools = ToolRegistry(tools=[CodeExecutionTool()])
    agent = CodingAgent(llm_provider=llm, tools=tools)

    result = agent.run("Write a python script to print hello")
    assert result.agent_name == "coding"
    assert result.answer == "Here is a simple python script: print('hello')"
    assert result.tool_name is None
    assert result.tool_output is None


def test_coding_agent_with_tool_call() -> None:
    first_resp = LLMResponse(
        content="",
        tool_call=LLMToolCall(
            name="execute_code",
            arguments={"language": "python", "code": "print('verified hello')"},
        ),
    )
    final_resp = LLMResponse(content="The code was executed and output verified: verified hello")

    llm = ScriptedLLMProvider([first_resp, final_resp])
    
    # Mock CodeExecutionTool.execute / run
    code_tool = CodeExecutionTool()
    code_tool.run = lambda args: "Exit code: 0\n\nstdout:\nverified hello\n"

    tools = ToolRegistry(tools=[code_tool])
    agent = CodingAgent(llm_provider=llm, tools=tools)

    result = agent.run("Write and test a python script that prints verified hello")
    assert result.agent_name == "coding"
    assert result.tool_name == "execute_code"
    assert result.tool_arguments == {"language": "python", "code": "print('verified hello')"}
    assert "verified hello" in result.tool_output
    assert "The code was executed and output verified" in result.answer
