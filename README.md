# AI OS Monolith

This is a local-first monolith with two apps:

- `apps/api`: FastAPI backend
- `apps/web`: Next.js frontend

The current foundation rules are intentionally strict:

- One backend process run locally with `uvicorn`
- One frontend process run locally with `next dev`
- Postgres only for persistence
- One active LLM provider behind an abstraction layer
- LangGraph orchestrates Planner, Research, and Knowledge agents
- JWT auth only
- No Redis, no queues, no vector DB, no Docker, no observability stack

The backend is structured for clean architecture so later agents, retrieval, caching, and external services can be added without a rewrite.

## Agent Graph

The backend uses LangGraph for the current multi-agent flow:

```text
user request -> planner node -> direct answer
                         |
                         -> research agent -> final answer
                         |
                         -> knowledge agent -> pgvector retrieval -> final answer
```

The Planner decides whether a request should be answered directly, routed to Research, or routed to Knowledge. Research can use the shared `ToolRegistry`. Knowledge embeds the query, searches the current user's document chunks in Postgres/pgvector, and answers from retrieved context.

New agents register in `apps/api/app/agents/registry.py`; graph construction reads from that registry.

## Runbook

Create `apps/api/.env`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
JWT_SECRET_KEY=replace-with-a-long-random-value
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash
LLM_API_KEY=your-gemini-api-key
LLM_MAX_OUTPUT_TOKENS=2048
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
LLM_CACHE_TTL_SECONDS=3600
CONVERSATION_CACHE_TTL_SECONDS=300
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
ENCRYPTION_KEY=generate-with-fernet
FRONTEND_ORIGIN=http://localhost:3000
```

Generate `ENCRYPTION_KEY` with:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

BYOK uses Fernet with a single server-held key as a temporary stopgap. Real KMS-backed key management and rotation are a later security hardening item, not part of this local-first phase.

To switch to Groq:

```env
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
LLM_API_KEY=your-groq-api-key
```

Create `apps/web/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the backend with `uv` and a local virtual environment:

```powershell
cd apps/api
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

The API also runs `alembic upgrade head` on startup unless `ENVIRONMENT=test`.

Run the frontend:

```powershell
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`, register a user, create a conversation, and send a planner request. The graph can answer directly or route to Research. Tool calls are recorded in `tool_calls`, including the agent that invoked the tool.

For lightweight RAG, paste text into the Knowledge panel. The backend stores `documents` and `document_chunks`, using the Neon Postgres `vector` extension with Gemini embeddings. Ask a knowledge-flavored question in chat and the Planner can route it to the Knowledge agent. Retrieval audits are stored in `retrievals` with retrieved chunk IDs and scores.

BYOK endpoints:

```text
POST /users/me/api-keys
DELETE /users/me/api-keys/{provider}
```

The API never returns stored key material. It only returns provider metadata when a key is set or updated. Saving a key also makes that provider the user's active provider. If a user has exactly one saved key and no explicit preference, that provider is used; otherwise the server default is used.

RAG endpoints:

```text
POST /documents
```

Run backend tests:

```powershell
cd apps/api
.\.venv\Scripts\Activate.ps1
pytest
```
