-- =============================================================
-- NOTEBOOKLM LITE — Initial Database Schema
-- =============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================
-- ENUMS
-- =============================================================

CREATE TYPE document_status AS ENUM (
    'uploaded',
    'parsing',
    'indexed',
    'failed'
);

CREATE TYPE message_role AS ENUM (
    'user',
    'assistant',
    'system'
);

-- =============================================================
-- TABLES
-- =============================================================

-- Notebooks: top-level containers for documents and conversations
CREATE TABLE IF NOT EXISTS notebooks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id    UUID,                          -- future auth support
    title       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Documents: files uploaded to a notebook
CREATE TABLE IF NOT EXISTS documents (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notebook_id  UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    filename     TEXT NOT NULL,
    storage_key  TEXT NOT NULL,               -- object-storage key
    sha256       TEXT NOT NULL,               -- for deduplication
    page_count   INTEGER,
    status       document_status NOT NULL DEFAULT 'uploaded',
    error_msg    TEXT,                        -- populated on failure
    file_size    BIGINT,
    mime_type    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_notebook_sha256 UNIQUE (notebook_id, sha256)
);

-- Chunks: segments of parsed document text with page metadata
CREATE TABLE IF NOT EXISTS chunks (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  INTEGER NOT NULL,
    page_start   INTEGER NOT NULL,
    page_end     INTEGER NOT NULL,
    text         TEXT NOT NULL,
    char_count   INTEGER GENERATED ALWAYS AS (length(text)) STORED,
    tsv          TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Embeddings: vector representations of chunks (separate table for model flexibility)
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id    UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    model       TEXT NOT NULL,
    embedding   VECTOR(1536),               -- dimension configured via env
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Conversations: chat sessions tied to a notebook
CREATE TABLE IF NOT EXISTS conversations (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notebook_id  UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    title        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Messages: individual turns in a conversation
CREATE TABLE IF NOT EXISTS messages (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id  UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role             message_role NOT NULL,
    content          TEXT NOT NULL,
    prompt_version   TEXT,                  -- track prompt changes
    model_name       TEXT,                  -- which LLM was used
    not_found        BOOLEAN DEFAULT FALSE, -- true when answer couldn't be sourced
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Citations: traceable references linking message sentences to chunks/pages
CREATE TABLE IF NOT EXISTS citations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id  UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    chunk_id    UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    marker      INTEGER NOT NULL,           -- [1], [2], … shown to user
    quote       TEXT NOT NULL,             -- verbatim text cited
    page        INTEGER NOT NULL,          -- exact page number
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- INDEXES
-- =============================================================

-- Vector index — HNSW for approximate nearest-neighbour search
CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw
    ON embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search index on chunk text
CREATE INDEX IF NOT EXISTS idx_chunks_tsv
    ON chunks USING gin (tsv);

-- B-tree index for fast chunk lookup by document
CREATE INDEX IF NOT EXISTS idx_chunks_document_id
    ON chunks (document_id);

-- B-tree index for fast message lookup by conversation
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages (conversation_id);

-- B-tree index for fast document lookup by notebook
CREATE INDEX IF NOT EXISTS idx_documents_notebook_id
    ON documents (notebook_id);

-- B-tree index for fast conversation lookup by notebook
CREATE INDEX IF NOT EXISTS idx_conversations_notebook_id
    ON conversations (notebook_id);

-- B-tree index for citations by message
CREATE INDEX IF NOT EXISTS idx_citations_message_id
    ON citations (message_id);

-- =============================================================
-- HELPER FUNCTION: update updated_at automatically
-- =============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_notebooks_updated_at
    BEFORE UPDATE ON notebooks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
