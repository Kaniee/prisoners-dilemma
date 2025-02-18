#!/bin/bash

set -e

# Database configuration
DB_NAME="tournament_db"
DB_USER="tournament_user"
DB_PASSWORD="tournament_pass"

# Check if the user exists and drop the user
USER_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'")

if [ "$USER_EXISTS" == "1" ]; then
    echo "User '$DB_USER' already exists. Skipping."
else
    # Create user and database
    echo "Creating database user..."
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
fi

# Check if the database already exists
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

if [ "$DB_EXISTS" == "1" ]; then
    echo "Database '$DB_NAME' already exists. Skipping."
else
    # Create the database
    echo "Creating database..."
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

    # Apply the schema
#     echo "Applying database schema..."
#     PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME -f schema.sql
fi

echo "Database setup complete."
