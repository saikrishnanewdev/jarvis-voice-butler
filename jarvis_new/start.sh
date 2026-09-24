#!/bin/bash
COMPOSE_CMD="sudo docker-compose"
if sudo docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="sudo docker compose"
fi

echo "Starting Jarvis Voice Butler containers..."
$COMPOSE_CMD down --remove-orphans >/dev/null 2>&1 || true
$COMPOSE_CMD up -d --build
echo ""
echo "Current Container Status:"
$COMPOSE_CMD ps
