-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a sample table with vector column for testing
CREATE TABLE IF NOT EXISTS embeddings_test (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(1536),  -- OpenAI embedding size
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS embeddings_test_embedding_idx ON embeddings_test 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Insert some sample data for testing
INSERT INTO embeddings_test (content, embedding, metadata) VALUES 
('Sample text 1', array_fill(0.1, ARRAY[1536])::vector, '{"source": "test"}'),
('Sample text 2', array_fill(0.2, ARRAY[1536])::vector, '{"source": "test"}'),
('Sample text 3', array_fill(0.3, ARRAY[1536])::vector, '{"source": "test"}')
ON CONFLICT DO NOTHING;

-- Create function for similarity search
CREATE OR REPLACE FUNCTION similarity_search(
    query_embedding vector(1536),
    similarity_threshold float DEFAULT 0.8,
    match_count int DEFAULT 10
)
RETURNS TABLE(
    id int,
    content text,
    similarity float,
    metadata jsonb
)
LANGUAGE sql
AS $$
SELECT 
    embeddings_test.id,
    embeddings_test.content,
    1 - (embeddings_test.embedding <=> query_embedding) AS similarity,
    embeddings_test.metadata
FROM embeddings_test
WHERE 1 - (embeddings_test.embedding <=> query_embedding) > similarity_threshold
ORDER BY embeddings_test.embedding <=> query_embedding
LIMIT match_count;
$$;