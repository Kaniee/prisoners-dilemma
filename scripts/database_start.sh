#!/bin/bash

# Database configuration
DB_NAME="tournament_db"

# Create the database
echo "Creating database..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"

# Apply the schema using the default 'postgres' superuser
echo "Applying database schema..."
sudo -u postgres psql -d $DB_NAME -f schema.sql

echo "Database setup complete."
