-- Setup database initialization - this runs as postgres user
-- The database 'california_schools' and user 'thoth_user' are already created by Docker environment

-- Grant additional permissions for Supabase-style functionality
GRANT ALL PRIVILEGES ON DATABASE california_schools TO thoth_user;

-- Connect to the target database
\c california_schools

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO thoth_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO thoth_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO thoth_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO thoth_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO thoth_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO thoth_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO thoth_user;