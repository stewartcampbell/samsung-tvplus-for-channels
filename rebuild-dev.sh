#!/bin/bash

docker compose pull
docker compose -f docker-compose-dev.yml down
docker compose -f docker-compose-dev.yml rm -f
docker compose -f docker-compose-dev.yml build --no-cache
docker compose -f docker-compose-dev.yml up -d --force-recreate
docker compose logs -f
