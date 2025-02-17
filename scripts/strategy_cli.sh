#!/bin/bash
# ./strategy_cli.sh add "Always Cooperate" "pd-always-cooperate"
# ./strategy_cli.sh add "Always Defect" "pd-always-defect"
# ./strategy_cli.sh add "Grudger" "pd-grudger"
# ./strategy_cli.sh add "Pavlov" "pd-pavlov"
# ./strategy_cli.sh add "Random" "pd-random"
# ./strategy_cli.sh add "Tit for Tat" "pd-tit-for-tat"

DB_NAME="tournament_db"
DB_USER="tournament_user"
DB_HOST="localhost"

function list_strategies() {
    psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "SELECT id, name, docker_image, created_at FROM strategies;"
}

function add_strategy() {
    local name="$1"
    local docker_image="$2"
    psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "INSERT INTO strategies (name, docker_image) VALUES ('$name', '$docker_image');"
    echo "Strategy added."
}

function delete_strategy() {
    local id="$1"
    psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "DELETE FROM strategies WHERE id = $id;"
    echo "Strategy deleted."
}

function update_strategy() {
    local id="$1"
    local new_name="$2"
    local new_docker_image="$3"
    
    if [[ -n "$new_name" ]]; then
        psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "UPDATE strategies SET name = '$new_name' WHERE id = $id;"
        echo "Strategy name updated."
    fi
    
    if [[ -n "$new_docker_image" ]]; then
        psql "postgresql://$DB_USER:tournament_pass@$DB_HOST/$DB_NAME" -c "UPDATE strategies SET docker_image = '$new_docker_image' WHERE id = $id;"
        echo "Strategy Docker image updated."
    fi
}

function usage() {
    echo "Usage: $0 {list|add <name> <docker_image>|delete <id>|update <id> [new_name] [new_docker_image]}"
    exit 1
}

if [ "$#" -lt 1 ]; then
    usage
fi

case "$1" in
    list)
        list_strategies
        ;;
    add)
        if [ "$#" -ne 3 ]; then usage; fi
        add_strategy "$2" "$3"
        ;;
    delete)
        if [ "$#" -ne 2 ]; then usage; fi
        delete_strategy "$2"
        ;;
    update)
        if [ "$#" -lt 2 ]; then usage; fi
        update_strategy "$2" "$3" "$4"
        ;;
    *)
        usage
        ;;
esac
