from datetime import datetime, timezone
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversations: Mapped[list["ConversationModel"]] = relationship(back_populates="user")
    api_keys: Mapped[list["UserApiKeyModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    documents: Mapped[list["DocumentModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped[UserModel] = relationship(back_populates="conversations")
    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="MessageModel.created_at"
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation: Mapped[ConversationModel] = relationship(back_populates="messages")
    tool_calls: Mapped[list["ToolCallModel"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class ToolCallModel(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False, default="planner")
    arguments: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation: Mapped[ConversationModel] = relationship()
    message: Mapped[MessageModel] = relationship(back_populates="tool_calls")


class UserApiKeyModel(Base):
    __tablename__ = "user_api_keys"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_api_keys_user_provider"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="api_keys")


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, default="pasted_text")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunkModel"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunkModel.chunk_index"
    )


class DocumentChunkModel(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dimensions), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    document: Mapped[DocumentModel] = relationship(back_populates="chunks")


class RetrievalModel(Base):
    __tablename__ = "retrievals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False, default="knowledge")
    query: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_ids: Mapped[str] = mapped_column(Text, nullable=False)
    scores: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
