#!/bin/bash

echo "Starting Ollama and downloading model..."

# Start services
docker-compose up -d ollama

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
until curl -s http://localhost:11434/api/version > /dev/null; do
    sleep 2
done

# Pull the model
echo "Pulling llama3.2 model..."
docker exec ollama-server ollama pull llama3.2

echo "Setup complete! Ollama is running with llama3.2 model."