#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  -- Create user if not exists
  DO
  \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
  END
  \$\$;

  -- Create database if not exists
  SELECT 'CREATE DATABASE $DB_NAME'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

  -- Connect to the new database
  \c $DB_NAME

  -- Grant permissions on public schema
  ALTER SCHEMA public OWNER TO $DB_USER;
  GRANT ALL ON SCHEMA public TO $DB_USER;
  GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

  -- Grant permissions to create enum types
  GRANT CREATE ON DATABASE $DB_NAME TO $DB_USER;
EOSQL
