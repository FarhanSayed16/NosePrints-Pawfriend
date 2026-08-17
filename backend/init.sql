-- NosePrints-Pawfriend — Database Initialization
-- This runs automatically when the PostgreSQL container starts for the first time.

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
