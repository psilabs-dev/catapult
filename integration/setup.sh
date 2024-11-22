#!/bin/bash

docker compose -f integration/docker-compose.yml --profile server up --build -d

# add "lanraragi" API key.
docker exec -it redis bash -c "redis-cli <<EOF
SELECT 2
HSET LRR_CONFIG apikey lanraragi
EOF"

# enable nofun mode.
docker exec -it redis bash -c "redis-cli <<EOF
SELECT 2
HSET LRR_CONFIG nofunmode 1
EOF"

# make content folder uploadable.
docker exec -it lanraragi /bin/sh -c "chown -R koyomi: content"
