"""add documents retrievals and pgvector

Revision ID: 0006_rag_pgvector
Revises: 0005_users_preferred_provider
Create Date: 2026-07-12 00:05:00
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


from app.core.config import settings


revision = "0006_rag_pgvector"
down_revision = "0005_users_preferred_provider"
branch_labels = None
depends_on = None


EMBEDDING_DIMENSIONS = settings.embedding_dimensions


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    if "documents" not in existing_tables:
        op.create_table(
            "documents",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("source_type", sa.String(length=80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False)

    if "document_chunks" not in existing_tables:
        op.create_table(
            "document_chunks",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"], unique=False)

    if "retrievals" not in existing_tables:
        op.create_table(
            "retrievals",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("conversation_id", sa.String(length=36), nullable=False),
            sa.Column("message_id", sa.String(length=36), nullable=False),
            sa.Column("agent_name", sa.String(length=80), nullable=False),
            sa.Column("query", sa.Text(), nullable=False),
            sa.Column("chunk_ids", sa.Text(), nullable=False),
            sa.Column("scores", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_retrievals_conversation_id"), "retrievals", ["conversation_id"], unique=False)
        op.create_index(op.f("ix_retrievals_message_id"), "retrievals", ["message_id"], unique=False)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "retrievals" in existing_tables:
        op.drop_index(op.f("ix_retrievals_message_id"), table_name="retrievals")
        op.drop_index(op.f("ix_retrievals_conversation_id"), table_name="retrievals")
        op.drop_table("retrievals")
    if "document_chunks" in existing_tables:
        op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
        op.drop_table("document_chunks")
    if "documents" in existing_tables:
        op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
        op.drop_table("documents")
