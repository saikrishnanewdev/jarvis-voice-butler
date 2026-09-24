#!/bin/bash
COMPOSE_CMD="sudo docker-compose"
if sudo docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="sudo docker compose"
fi

echo "Stopping Jarvis Voice Butler containers..."
$COMPOSE_CMD down
