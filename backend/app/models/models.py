"""
SQLAlchemy ORM models — aligned exactly with the specification schema.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    FetchedValue,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


# ─── Notebooks ───────────────────────────────────────────────────────────────

class Notebook(Base):
    __tablename__ = "notebooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    documents = relationship("Document", back_populates="notebook", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="notebook", cascade="all, delete-orphan")


# ─── Documents ───────────────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("notebook_id", "sha256", name="uq_notebook_sha256"),
        Index("idx_documents_notebook_id", "notebook_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    filename = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=False)
    sha256 = Column(Text, nullable=False)
    page_count = Column(Integer, nullable=True)
    status = Column(
        Enum("uploaded", "parsing", "indexed", "failed", name="document_status"),
        nullable=False,
        default="uploaded",
    )
    error_msg = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    notebook = relationship("Notebook", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


# ─── Chunks ──────────────────────────────────────────────────────────────────

class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("idx_chunks_document_id", "document_id"),
        Index("idx_chunks_tsv", "tsv", postgresql_using="gin"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    tsv = Column(TSVECTOR, FetchedValue())  # populated automatically by PostgreSQL generated column
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    document = relationship("Document", back_populates="chunks")
    embedding = relationship("Embedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="chunk", cascade="all, delete-orphan")


# ─── Embeddings ──────────────────────────────────────────────────────────────

class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        Index("idx_embeddings_hnsw", "embedding", postgresql_using="hnsw",
              postgresql_with={"m": 16, "ef_construction": 64},
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )

    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True)
    model = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    chunk = relationship("Chunk", back_populates="embedding")


# ─── Conversations ────────────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversations_notebook_id", "notebook_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    notebook = relationship("Notebook", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")


# ─── Messages ────────────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum("user", "assistant", "system", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    prompt_version = Column(Text, nullable=True)
    model_name = Column(Text, nullable=True)
    not_found = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
    citations = relationship("Citation", back_populates="message", cascade="all, delete-orphan")


# ─── Citations ────────────────────────────────────────────────────────────────

class Citation(Base):
    __tablename__ = "citations"
    __table_args__ = (
        Index("idx_citations_message_id", "message_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    marker = Column(Integer, nullable=False)
    quote = Column(Text, nullable=False)
    page = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    message = relationship("Message", back_populates="citations")
    chunk = relationship("Chunk", back_populates="citations")
