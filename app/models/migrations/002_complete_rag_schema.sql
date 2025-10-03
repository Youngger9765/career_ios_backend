-- Complete RAG Schema Migration (from career_app)
-- This extends 001_add_rag_tables.sql with agents, collections, and advanced features

-- Note: Run 001_add_rag_tables.sql first if not already done

-- 1. Create agents table (for multi-agent RAG systems)
CREATE TABLE IF NOT EXISTS agents (
    id BIGSERIAL PRIMARY KEY,
    slug VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    active_version_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create agent_versions table
CREATE TABLE IF NOT EXISTS agent_versions (
    id BIGSERIAL PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    state VARCHAR(50) DEFAULT 'draft',
    config_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),
    UNIQUE(agent_id, version)
);

-- 3. Add foreign key for active version
ALTER TABLE agents
    ADD CONSTRAINT fk_active_version
    FOREIGN KEY (active_version_id)
    REFERENCES agent_versions(id)
    ON DELETE SET NULL;

-- 4. Create collections table (document grouping)
CREATE TABLE IF NOT EXISTS collections (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create collection_items table (many-to-many)
CREATE TABLE IF NOT EXISTS collection_items (
    collection_id BIGINT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    doc_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (collection_id, doc_id)
);

-- 6. Create pipeline_runs table (processing tracking)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    scope VARCHAR(50) NOT NULL,
    target_id BIGINT,
    status VARCHAR(50) DEFAULT 'queued',
    steps_json JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    error_msg TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Create chat_logs table (conversation history)
CREATE TABLE IF NOT EXISTS chat_logs (
    id BIGSERIAL PRIMARY KEY,
    agent_id BIGINT REFERENCES agents(id) ON DELETE SET NULL,
    version_id BIGINT REFERENCES agent_versions(id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    answer TEXT,
    citations_json JSONB DEFAULT '[]'::jsonb,
    tokens_in INTEGER,
    tokens_out INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Create indexes
CREATE INDEX IF NOT EXISTS idx_agents_slug ON agents(slug);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agent_versions_agent_id ON agent_versions(agent_id);
CREATE INDEX IF NOT EXISTS idx_collection_items_doc_id ON collection_items(doc_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_target_id ON pipeline_runs(target_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_chat_logs_agent_id ON chat_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON chat_logs(created_at DESC);

-- 9. Add triggers for updated_at
DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 10. Create advanced vector search function with collection filtering
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(1536),
    match_count int DEFAULT 5,
    filter_collection_id bigint DEFAULT NULL
)
RETURNS TABLE (
    chunk_id bigint,
    doc_id bigint,
    text text,
    similarity float,
    document_title varchar(500),
    meta_json jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id as chunk_id,
        c.doc_id,
        c.text,
        1 - (e.embedding <=> query_embedding) as similarity,
        d.title as document_title,
        c.meta_json
    FROM embeddings e
    JOIN chunks c ON e.chunk_id = c.id
    JOIN documents d ON c.doc_id = d.id
    LEFT JOIN collection_items ci ON d.id = ci.doc_id
    WHERE
        (filter_collection_id IS NULL OR ci.collection_id = filter_collection_id)
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Comments for documentation
COMMENT ON TABLE agents IS 'AI agents configuration and versioning';
COMMENT ON TABLE agent_versions IS 'Version history for agents';
COMMENT ON TABLE collections IS 'Document collections for grouping and filtering';
COMMENT ON TABLE collection_items IS 'Documents in each collection';
COMMENT ON TABLE pipeline_runs IS 'RAG pipeline execution tracking';
COMMENT ON TABLE chat_logs IS 'Chat conversation history with RAG';
COMMENT ON FUNCTION search_similar_chunks IS 'Advanced vector search with optional collection filtering';

-- Done
SELECT 'Complete RAG schema migration completed successfully!' as status;
