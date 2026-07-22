import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Document, RetrievedChunk, Retrieval
from app.infrastructure.models import DocumentChunkModel, DocumentModel, RetrievalModel


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_with_chunks(
        self,
        user_id: str,
        title: str,
        source_type: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> Document:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        document = DocumentModel(user_id=user_id, title=title, source_type=source_type)
        self.session.add(document)
        self.session.flush()
        for index, (content, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            self.session.add(
                DocumentChunkModel(
                    document_id=document.id,
                    chunk_index=index,
                    content=content,
                    embedding=embedding,
                )
            )
        self.session.commit()
        self.session.refresh(document)
        return Document(
            id=document.id,
            user_id=document.user_id,
            title=document.title,
            source_type=document.source_type,
            created_at=document.created_at,
        )

    def list_for_user(self, user_id: str) -> list[Document]:
        documents = self.session.scalars(
            select(DocumentModel).where(DocumentModel.user_id == user_id).order_by(DocumentModel.created_at.desc())
        ).all()
        return [
            Document(
                id=doc.id,
                user_id=doc.user_id,
                title=doc.title,
                source_type=doc.source_type,
                created_at=doc.created_at,
            )
            for doc in documents
        ]


class RetrievalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, user_id: str, embedding: list[float], limit: int = 4) -> list[RetrievedChunk]:
        if self.session.bind and self.session.bind.dialect.name == "sqlite":
            chunks = self.session.scalars(
                select(DocumentChunkModel)
                .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
                .where(DocumentModel.user_id == user_id)
                .limit(limit)
            ).all()
            return [
                RetrievedChunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=0.1,
                )
                for chunk in chunks
            ]

        distance = DocumentChunkModel.embedding.cosine_distance(embedding).label("score")
        rows = self.session.execute(
            select(DocumentChunkModel, distance)
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            .where(DocumentModel.user_id == user_id)
            .order_by(distance)
            .limit(limit)
        ).all()
        return [
            RetrievedChunk(
                id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                score=float(score),
            )
            for chunk, score in rows
        ]

    def create(
        self,
        conversation_id: str,
        message_id: str,
        agent_name: str,
        query: str,
        chunk_ids: list[str],
        scores: list[float],
    ) -> Retrieval:
        retrieval = RetrievalModel(
            conversation_id=conversation_id,
            message_id=message_id,
            agent_name=agent_name,
            query=query,
            chunk_ids=json.dumps(chunk_ids),
            scores=json.dumps(scores),
        )
        self.session.add(retrieval)
        self.session.commit()
        self.session.refresh(retrieval)
        return Retrieval(
            id=retrieval.id,
            conversation_id=retrieval.conversation_id,
            message_id=retrieval.message_id,
            agent_name=retrieval.agent_name,
            query=retrieval.query,
            chunk_ids=retrieval.chunk_ids,
            scores=retrieval.scores,
            created_at=retrieval.created_at,
        )
