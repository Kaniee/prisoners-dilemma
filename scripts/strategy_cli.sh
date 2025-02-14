#!/bin/bash

DB_NAME="tournament_db"
DB_USER="tournament_user"
DB_HOST="localhost"

function list_strategies() {
    psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "SELECT id, name, docker_image, created_at FROM strategies;"
}

function add_strategy() {
    read -p "Enter strategy name: " name
    read -p "Enter Docker image: " docker_image
    psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "INSERT INTO strategies (name, docker_image) VALUES ('$name', '$docker_image');"
    echo "Strategy added."
}

function delete_strategy() {
    echo "Available strategies:"
    psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "SELECT id, name, docker_image FROM strategies;"
    read -p "Enter strategy ID to delete: " id
    psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "DELETE FROM strategies WHERE id = $id;"
    echo "Strategy deleted."
}

function usage() {
    echo "Usage: $0 {list|add|delete}"
    exit 1
}

if [ "$#" -ne 1 ]; then
    usage
fi

case "$1" in
    list)
        list_strategies
        ;;
    add)
        add_strategy
        ;;
    delete)
        delete_strategy
        ;;
    *)
        usage
        ;;
esac
