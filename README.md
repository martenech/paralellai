# paralellai – Long-Term Memory for Local LLMs

A self-hosted service that gives a local large language model persistent, searchable memory across conversations. Every message is stored with a vector embedding; on each new question the system retrieves semantically similar past exchanges and injects them into the prompt. A background **reflection agent** periodically summarises conversations and extracts higher-level insights about the user (patterns, goals, interests, knowledge), which are also available as memory.

Everything runs locally – no data is sent to external APIs.

## Motivation

LLMs are stateless: once a conversation ends, the model forgets it. Commercial assistants solve this with proprietary memory features. This project explores an open, inspectable architecture for long-term memory built from standard components:

- **episodic memory** – raw messages with embeddings, retrieved by semantic similarity;
- **short-term context** – the active conversation window cached in Redis;
- **reflective memory** – LLM-generated summaries and meta-insights produced asynchronously, similar to the reflection mechanism in *Generative Agents* (Park et al., 2023).

## Architecture

```
            ┌──────────────┐      ┌──────────────────────────┐
 CLI / API ─►   FastAPI    ├──────►  Ollama (llama3.2,        │
 clients    │   (app/)     │      │  nomic-embed-text)       │
            └──┬────────┬──┘      └──────────────────────────┘
               │        │
     ┌─────────▼──┐  ┌──▼──────────────────┐   ┌───────────────────┐
     │   Redis    │  │ PostgreSQL+pgvector │◄──┤ reflection worker │
     │ (context)  │  │ messages, embeddings│   │ every 5 min:      │
     └────────────┘  │ summaries, insights │   │ summaries, insights│
                     └─────────────────────┘   └───────────────────┘
```

| Component | Technology |
|---|---|
| LLM | Ollama, default model `llama3.2` |
| Embeddings | Ollama `nomic-embed-text` (768 d) or Sentence Transformers `all-MiniLM-L6-v2` (384 d) |
| API | FastAPI, SQLAlchemy 2, Pydantic 2 |
| Vector store | PostgreSQL 16 with pgvector (cosine distance) |
| Cache | Redis |
| Background jobs | asyncio reflection worker |

Key modules:

- `app/services/memory_manager.py` – semantic retrieval of similar past questions and answers (similarity threshold 0.7, relevance decays linearly over 30 days, up to 10 memories);
- `app/services/reflection_agent.py` – conversation summaries and user meta-insights (`pattern`, `goal`, `interest`, `knowledge`);
- `app/workers/reflection_worker.py` – runs the reflection agent every 5 minutes;
- `app/services/embedding.py`, `ollama_embeddings.py` – pluggable embedding providers.

## Quick start

Requirements: Docker with Docker Compose.

```bash
docker-compose up -d            # Ollama, Postgres+pgvector, Redis, API, reflection worker
./setup_ollama.sh               # pull the chat model (llama3.2)
./setup_embedding_model.sh      # pull the embedding model (nomic-embed-text)
```

The API runs at <http://localhost:8000>, interactive docs at <http://localhost:8000/docs>.

Configuration (environment variables, see `app/config.py`): `OLLAMA_CHAT_MODEL`, `EMBEDDING_PROVIDER` (`ollama` or `sentence_transformers`), `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `DATABASE_URL`, `REDIS_HOST`, `REDIS_PORT`.

## Usage

Interactive CLI:

```bash
python cli_client.py
```

| Command | Action |
|---|---|
| `/new [title]` | start a new conversation |
| `/list` | list conversations |
| `/switch <num>` | switch conversation |
| `/history` | show recent history |
| `/search <query>` | semantic search in the conversation |
| `/help`, `/quit` | help, exit |

One-shot message: `python chat.py "your message"`.

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | health check |
| POST | `/api/conversations/` | create a conversation |
| GET | `/api/conversations/{id}` | get a conversation |
| GET | `/api/conversations/user/{user_id}` | list a user's conversations |
| DELETE | `/api/conversations/{id}` | delete a conversation |
| POST | `/api/messages/chat` | send a message, get a memory-augmented answer |
| POST | `/api/messages/simple-chat` | chat without managing conversation IDs |
| GET | `/api/messages/conversation/{id}` | message history |
| GET | `/api/messages/search/{id}?query=…` | semantic search |
| GET | `/api/insights/conversation/{id}/summary` | conversation summary |
| POST | `/api/insights/conversation/{id}/summarize` | summarise now |
| GET | `/api/insights/user/{user_id}/insights` | user meta-insights |
| POST | `/api/insights/user/{user_id}/analyze` | extract insights now |
| GET | `/api/insights/summaries/recent` | recent summaries |
| GET | `/api/insights/search/insights` | search insights |

## Status

Research prototype. The database credentials in `docker-compose.yml` are local development defaults – change them before exposing the service on a network. `reset_database.sh` drops all stored conversations.

## References

- Park J.S. et al. (2023) *Generative Agents: Interactive Simulacra of Human Behavior.* UIST '23. doi:10.1145/3586183.3606763
- Lewis P. et al. (2020) *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS 33.

## Author

Developed by **Martin Pohorelský** ([martenech](https://github.com/martenech)).

## License

MIT, see [`LICENSE`](LICENSE).
