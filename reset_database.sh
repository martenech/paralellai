#!/bin/bash

echo "Resetting database with new schema..."

# Drop and recreate database
docker exec postgres-db psql -U llm_user -c "DROP DATABASE IF EXISTS llm_memory;"
docker exec postgres-db psql -U llm_user -c "CREATE DATABASE llm_memory;"

echo "Database reset complete!"