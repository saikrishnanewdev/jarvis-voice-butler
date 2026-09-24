#!/bin/bash
# Usage:
#   ./logs.sh                -> View live logs for all services
#   ./logs.sh agent-backend  -> View live logs for backend only
#   ./logs.sh frontend       -> View live logs for frontend only

if [ -z "$1" ]; then
    sudo docker-compose logs -f --tail=100
else
    sudo docker-compose logs -f --tail=100 "$1"
fi
