from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Conversation, Message
from app.infrastructure.models import ConversationModel, MessageModel, utc_now


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, user_id: str) -> list[Conversation]:
        conversations = self.session.scalars(
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.updated_at.desc())
        ).all()
        return [self._conversation_to_entity(conversation) for conversation in conversations]

    def get_for_user(self, conversation_id: str, user_id: str) -> Conversation | None:
        conversation = self.session.scalar(
            select(ConversationModel).where(
                ConversationModel.id == conversation_id,
                ConversationModel.user_id == user_id,
            )
        )
        return self._conversation_to_entity(conversation) if conversation else None

    def create(self, user_id: str, title: str) -> Conversation:
        conversation = ConversationModel(user_id=user_id, title=title)
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return self._conversation_to_entity(conversation)

    def list_messages(self, conversation_id: str) -> list[Message]:
        messages = self.session.scalars(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc())
        ).all()
        return [self._message_to_entity(message) for message in messages]

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
    ) -> Message:
        message = MessageModel(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_name=tool_name,
        )
        conversation = self.session.get(ConversationModel, conversation_id)
        if conversation:
            conversation.updated_at = utc_now()
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return self._message_to_entity(message)

    @staticmethod
    def _conversation_to_entity(conversation: ConversationModel) -> Conversation:
        return Conversation(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    @staticmethod
    def _message_to_entity(message: MessageModel) -> Message:
        return Message(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            tool_name=message.tool_name,
            created_at=message.created_at,
        )
