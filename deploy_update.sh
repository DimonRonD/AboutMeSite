#!/usr/bin/env bash
set -euo pipefail

mkdir -p logs database rag_source
chown -R 1000:1000 logs database rag_source
chmod -R 775 logs database rag_source

git fetch origin
git checkout main
git pull origin main
docker compose down
docker compose up --build -d
