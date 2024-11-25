#!/bin/bash

export MY_UID=$(id -u)
export MY_GID=$(id -g)
docker compose -f integration/docker-compose.yml down --volumes