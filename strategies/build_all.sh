#!/bin/bash

set -e

BASE_DIR="$(dirname "$0")"

for dir_path in "$BASE_DIR"/*/; do
    if [ -d "$dir_path" ]; then
        dir_name=$(basename "$dir_path")
        docker build --tag "${dir_name}" "$dir_path"
    fi
done
