# LLM Memory System

Systém pre LLM s perzistentnou pamäťou konverzácií využívajúci Ollama, PostgreSQL s pgvector a Redis.

## Architektúra

- **LLM**: Ollama s modelom llama3.2
- **API**: FastAPI (Python)
- **Databáza**: PostgreSQL s pgvector pre ukladanie konverzácií a embeddings
- **Cache**: Redis pre session a context management
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)

## Spustenie

```bash
# 1. Spustiť Ollama a stiahnuť model
./setup_ollama.sh

# 2. Spustiť všetky služby
docker-compose up -d

# 3. Spustiť API (dočasné riešenie)
docker run -d --name llm-api --network parallelai_default -p 8000:8000 \
  -e DATABASE_URL=postgresql://llm_user:llm_password@postgres:5432/llm_memory \
  -e REDIS_HOST=redis -e REDIS_PORT=6379 \
  -v $(pwd):/app python:3.11-slim \
  bash -c "cd /app && apt-get update && apt-get install -y build-essential && pip install -r requirements.txt && python -m app.main"
```

## Použitie

### CLI Klient

```bash
python cli_client.py
```

Príkazy:
- `/new [title]` - Vytvoriť novú konverzáciu
- `/list` - Zobraziť všetky konverzácie
- `/switch <num>` - Prepnúť na konverzáciu
- `/history` - Zobraziť poslednú históriu
- `/search <query>` - Vyhľadať v konverzácii
- `/help` - Zobraziť pomoc
- `/quit` - Ukončiť

### API Endpoints

- `GET /health` - Health check
- `POST /api/conversations` - Vytvoriť konverzáciu
- `GET /api/conversations/{id}` - Získať konverzáciu
- `GET /api/conversations/user/{user_id}` - Zoznam konverzácií používateľa
- `DELETE /api/conversations/{id}` - Zmazať konverzáciu
- `POST /api/messages/chat` - Poslať správu a získať odpoveď
- `GET /api/messages/conversation/{id}` - História správ
- `GET /api/messages/search/{id}?query=text` - Sémantické vyhľadávanie

### Test Script

```bash
python test_api.py
```

## Funkcie

1. **Perzistentná pamäť**: Všetky konverzácie sa ukladajú do PostgreSQL
2. **Context management**: LLM si pamätá kontext konverzácie cez Redis cache
3. **Sémantické vyhľadávanie**: Vyhľadávanie v histórii pomocou embeddingov
4. **Multi-user support**: Každý používateľ má svoje konverzácie
5. **REST API**: Jednoduché integrovanie s inými aplikáciami

## Štruktúra projektu

```
parallelAI/
├── app/
│   ├── api/              # API endpoints
│   ├── db/               # Database models a setup
│   ├── services/         # Business logic (LLM, embeddings, cache)
│   └── main.py           # FastAPI aplikácia
├── docker-compose.yml    # Docker služby
├── requirements.txt      # Python dependencies
├── cli_client.py         # CLI klient
└── test_api.py          # Test script
```