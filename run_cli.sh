#!/bin/bash
# Spustí CLI klienta pre LLM Memory systém

# Aktivuje virtual environment ak existuje
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Spustí CLI klienta
python cli_client.py