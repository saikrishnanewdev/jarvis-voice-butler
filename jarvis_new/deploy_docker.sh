#!/bin/bash
# One-command Docker Deployment script for Oracle Cloud VM

echo "========================================="
echo "  Deploying Jarvis AI Voice Butler Stack  "
echo "========================================="

# Ensure docker & docker compose are installed
if ! command -v docker &> /dev/null
then
    echo "Docker is not installed. Installing Docker..."
    sudo apt update && sudo apt install -y docker.io docker-compose-v2
    sudo usermod -aG docker $USER
fi

echo "Building and starting Docker containers..."
docker compose up -d --build

echo "========================================="
echo "  Deployment Complete!                   "
echo "  Frontend: http://<YOUR_VM_IP>:3000     "
echo "  Check Status: docker compose ps        "
echo "  View Logs:    docker compose logs -f   "
echo "========================================="
