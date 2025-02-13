#!/bin/bash

set -e

# Database configuration
DB_NAME="tournament_db"
DB_USER="tournament_user"

# Check if the database exists
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

if [ "$DB_EXISTS" != "1" ]; then
    echo "Database '$DB_NAME' does not exist. Nothing to delete."
else
    echo "Dropping database '$DB_NAME'..."
    sudo -u postgres psql -c "DROP DATABASE $DB_NAME;"
fi

# Check if the user exists and drop the user
USER_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'")

if [ "$USER_EXISTS" == "1" ]; then
    echo "Dropping user '$DB_USER'..."
    sudo -u postgres psql -c "DROP USER $DB_USER;"
else
    echo "User '$DB_USER' does not exist. No need to delete the user."
fi

echo "Database and user deletion process complete."
