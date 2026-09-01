-- ==============================================================================
-- HERO Cost Intelligence Database Extensions Initialization
-- Enables vector (pgvector) and pg_trgm for exact and semantic hybrid retrieval
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Verify extensions
SELECT extname, extversion FROM pg_extension;
