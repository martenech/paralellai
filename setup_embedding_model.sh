#!/bin/bash

echo "Setting up embedding model..."

# Pull nomic-embed-text model for Ollama
echo "Pulling nomic-embed-text model..."
docker exec ollama-server ollama pull nomic-embed-text

echo "Embedding model setup complete!"