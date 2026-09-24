#!/bin/bash
echo "Starting Jarvis Voice Butler containers..."
sudo docker-compose up -d --build
echo ""
echo "Current Container Status:"
sudo docker-compose ps
