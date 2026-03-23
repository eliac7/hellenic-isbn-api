# hellenic-isbn-api

Production-oriented FastAPI service that fetches book metadata by ISBN from the Greek National Library endpoint (`isbn.nlg.gr`).

## Features

- FastAPI async REST API
- NLG ISBN search (POST reverse-engineered flow)
- `curl_cffi` client with Chrome impersonation
- HTML parsing via BeautifulSoup4
- Unified response model
- In-memory cache with optional Redis (Upstash-compatible)
- Simple per-IP rate limiting
- Docker support

## Project structure

```text
app/
  main.py
  config.py
  dependencies.py
  routes/
  services/
  parsers/
  models/
  utils/
```

## API

### GET `/books/{isbn}`

Response:

```json
{
  "source": "nlg",
  "title": "string | null",
  "authors": ["string"],
  "publisher": "string | null",
  "year": "string | null",
  "isbn": "string",
  "cover": "string | null"
}
```

Health:

- `GET /health`
- `GET /search/title?title=<query>&details=true&details_limit=10`

## Local run

1. Create virtual environment and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Optional config:

```bash
cp .env.example .env
```

3. Start server:

```bash
uvicorn app.main:app --reload
```

## Docker

Build and run:

```bash
docker build -t hellenic-isbn-api .
docker run --rm -p 8000:8000 --env-file .env hellenic-isbn-api
```

## Environment variables

- `REDIS_URL` (optional): If set, Redis (TCP) cache is used
- `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` (optional): If both are set, Upstash REST cache is used
- `CURL_IMPERSONATE` (default: `chrome124`)
- `SSL_VERIFY` (default: `true`)
- `SSL_FALLBACK_INSECURE` (default: `true`, testing only)
- `CACHE_TTL_SECONDS` (default: `3600`)
- `RATE_LIMIT_REQUESTS` (default: `60`)
- `RATE_LIMIT_WINDOW_SECONDS` (default: `60`)
- `REQUEST_TIMEOUT_SECONDS` (default: `12`)

## Notes

- ISBN input is normalized (dashes/spaces removed).
- NLG lookup attempts full ISBN split first, then retries with partial ISBN fragments.
- If NLG returns no match, the API responds with `404`.
- Title search endpoint posts to NLG search form and returns structured results.
- For richer metadata from record pages, use `details=true` (with `details_limit` to control calls).
