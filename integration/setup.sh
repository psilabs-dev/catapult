#!/bin/bash

docker compose -f integration/docker-compose.yml --profile server up -d
docker exec -it redis bash -c "redis-cli <<EOF
SELECT 2
HSET LRR_CONFIG apikey lanraragi
EOF"
docker exec -it lanraragi /bin/sh -c "chown -R koyomi: content"
