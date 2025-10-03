-- RAG Tables Migration
-- Add pgvector extension and tables for RAG functionality

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Datasources table (PDF, URL, etc.)
CREATE TABLE IF NOT EXISTS datasources (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    source_uri TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_datasources_type ON datasources(type);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    datasource_id INTEGER NOT NULL REFERENCES datasources(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    bytes INTEGER,
    pages INTEGER,
    meta_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_datasource_id ON documents(datasource_id);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    meta_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX idx_chunks_ordinal ON chunks(doc_id, ordinal);

-- Embeddings table (1536 dimensions for text-embedding-3-small)
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER NOT NULL UNIQUE REFERENCES chunks(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_embeddings_chunk_id ON embeddings(chunk_id);

-- Create HNSW index for fast vector similarity search
-- Using cosine distance (<=>) as it's commonly used for text embeddings
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw
ON embeddings USING hnsw (embedding vector_cosine_ops);

-- Optional: Create IVFFlat index (alternative to HNSW, faster build, slower query)
-- Uncomment if you prefer IVFFlat or have specific requirements
-- CREATE INDEX IF NOT EXISTS idx_embeddings_vector_ivfflat
-- ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update documents.updated_at
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE datasources IS 'Source of documents (PDF files, URLs, etc.)';
COMMENT ON TABLE documents IS 'Document metadata and tracking';
COMMENT ON TABLE chunks IS 'Text chunks extracted from documents';
COMMENT ON TABLE embeddings IS 'Vector embeddings for semantic search';
COMMENT ON INDEX idx_embeddings_vector_hnsw IS 'HNSW index for fast cosine similarity search on embeddings';
