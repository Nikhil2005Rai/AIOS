from sqlalchemy.orm import Session

from app.domain.entities import ToolCall
from app.infrastructure.models import ToolCallModel


class ToolCallRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        conversation_id: str,
        message_id: str,
        tool_name: str,
        agent_name: str,
        arguments: str,
        output: str,
    ) -> ToolCall:
        tool_call = ToolCallModel(
            conversation_id=conversation_id,
            message_id=message_id,
            tool_name=tool_name,
            agent_name=agent_name,
            arguments=arguments,
            output=output,
        )
        self.session.add(tool_call)
        self.session.commit()
        self.session.refresh(tool_call)
        return ToolCall(
            id=tool_call.id,
            conversation_id=tool_call.conversation_id,
            message_id=tool_call.message_id,
            tool_name=tool_call.tool_name,
            agent_name=tool_call.agent_name,
            arguments=tool_call.arguments,
            output=tool_call.output,
            created_at=tool_call.created_at,
        )
