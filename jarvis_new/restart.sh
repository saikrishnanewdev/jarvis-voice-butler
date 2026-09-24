#!/bin/bash
echo "Restarting Jarvis Voice Butler containers..."
sudo docker-compose restart
echo ""
echo "Current Container Status:"
sudo docker-compose ps
