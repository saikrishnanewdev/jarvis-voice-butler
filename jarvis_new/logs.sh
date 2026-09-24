#!/bin/bash
COMPOSE_CMD="sudo docker-compose"
if sudo docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="sudo docker compose"
fi

if [ -z "$1" ]; then
    $COMPOSE_CMD logs -f --tail=100
else
    $COMPOSE_CMD logs -f --tail=100 "$1"
fi
