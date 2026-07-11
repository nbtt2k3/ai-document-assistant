# Environment Setup

This project has three runnable parts, each with its own `.env.example` file, plus a root `.env.example` for Docker Compose.

## Files

- `.env.example` at the repo root: Docker Compose values and shared secrets.
- `web-api/.env.example`: backend API, database, auth, and AI Agent URL.
- `ai-agent/.env.example`: RAG/OCR service, model providers, storage paths, and retrieval tuning.
- `frontend/.env.example`: Next.js public API URL.

Copy the relevant example before running a service locally:

```powershell
Copy-Item .env.example .env
Copy-Item web-api\.env.example web-api\.env
Copy-Item ai-agent\.env.example ai-agent\.env
Copy-Item frontend\.env.example frontend\.env.local
```

## Docker Compose

`docker-compose.yml` runs the full local stack:

- `frontend` serves the Next.js UI on port 3000.
- `web-api` connects to Postgres through `db:5432`.
- `web-api` calls `ai-agent` through `http://ai-agent:8001`.
- `ai-agent` calls host Ollama through `http://host.docker.internal:11434`.
- Runtime data stays under `/app/storage` and `/app/flashrank_cache` inside the container.

## Secrets

Do not commit real `.env` files. The `.env.example` files are safe examples only.
