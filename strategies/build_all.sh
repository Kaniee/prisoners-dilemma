#!/bin/bash
cd "$(dirname "$0")"

for strategy in */; do
    if [ -d "$strategy" ]; then
        cd "$strategy"
        docker build -t "pd-${strategy%/}" .
        cd ..
    fi
done
