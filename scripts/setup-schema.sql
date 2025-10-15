-- Create dev_v2 schema for isolated database development
CREATE SCHEMA IF NOT EXISTS dev_v2;

-- Grant necessary permissions (adjust username as needed)
-- GRANT ALL ON SCHEMA dev_v2 TO your_username;
-- GRANT ALL ON ALL TABLES IN SCHEMA dev_v2 TO your_username;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA dev_v2 TO your_username;

-- You can verify schema creation with:
-- SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'dev_v2';
