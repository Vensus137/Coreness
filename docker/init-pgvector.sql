-- Automatic installation of pgvector extension when creating database
-- This script runs automatically on first PostgreSQL initialization
-- through /docker-entrypoint-initdb.d/ mechanism

-- Install pgvector extension in core_db database
-- IF NOT EXISTS prevents error if extension is already installed
CREATE EXTENSION IF NOT EXISTS vector;

