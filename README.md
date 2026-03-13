# Enterprise RAG SaaS (Django + DRF + pgvector + Redis + Celery)

This project supports multi-tenant (organization-scoped) document upload + RAG chat.

## Quick start (Docker)

1. Create/edit `.env` (see existing `.env` keys).
2. Start services:
   - `docker compose up --build`
3. Open Swagger:
   - `http://localhost:8000/api/docs/`

## MVP Frontend (Streamlit)

This repo includes a simple Streamlit UI for the full MVP flow: register → login → invite → accept → upload docs → search → chat.

### Run with Docker

- Start everything (includes `frontend`):
  - `docker compose up --build`
- Open Streamlit:
  - `http://localhost:8501`

### Run locally (without Docker)

- Install frontend deps:
  - `pip install -r frontend/requirements.txt`
- Set API base URL (optional):
  - `API_BASE_URL=http://localhost:8000`
- Run:
  - `streamlit run frontend/streamlit_app.py`

## Swagger-first testing (recommended)

### 1) Register an organization (public)

Endpoint: `POST /api/auth/register/`

Payload:
```json
{
  "organization_name": "Acme Corp",
  "organization_slug": "acme",
  "admin_email": "admin@acme.com",
  "admin_password": "AdminPassw0rd!"
}
```

Notes:
- `organization_slug` is optional. If omitted, it is derived from the name and capped to the DB field max length.

### 2) Login to get JWT (public)

Endpoint: `POST /api/auth/login/`

Payload:
```json
{
  "email": "admin@acme.com",
  "password": "AdminPassw0rd!"
}
```

Copy the `access` token from the response.

### 3) Authorize in Swagger (required for all protected endpoints)

In Swagger UI, click **Authorize** and paste:

`Bearer <access_token>`

Swagger is configured to persist authorization (so it stays across refreshes).

## Invitation flow (org admin)

### 4) Create an invitation (org admin only)

Endpoint: `POST /api/organizations/invitations/`

Payload:
```json
{
  "email": "user1@acme.com",
  "role": "member",
  "expires_in_days": 7
}
```

Response includes:
- `token` (invite token)
- `accept_url` (if `FRONTEND_URL` is configured, it will be a frontend link; otherwise it will point to the API accept endpoint)

### 5) Accept invitation (public)

Endpoint: `POST /api/auth/invitations/accept/`

Payload:
```json
{
  "token": "<invite_token>",
  "password": "UserPassw0rd!"
}
```

Then login as the invited user using `POST /api/auth/login/` and authorize in Swagger again (optional if you want to test as the member).

## Documents (organization-scoped)

### Upload a policy document (org admin only)

Endpoint: `POST /api/documents/documents/`

Swagger steps:
1. Click **Try it out**
2. Upload using the `file` field (multipart form-data)
3. Execute

Notes:
- The document is processed asynchronously by Celery (chunking + embeddings).

### Search policy chunks (org members)

Endpoint: `POST /api/documents/search/`

Payload:
```json
{ "query": "What is our annual leave policy?" }
```

## Chat (organization-scoped)

### Create a chat session (org members)

Endpoint: `POST /api/chat/sessions/`

Payload (optional):
```json
{ "title": "HR policies" }
```

Response includes `session_id`.

### Send a message (org members)

Endpoint: `POST /api/chat/sessions/{session_id}/messages/`

Payload:
```json
{
  "content": "What is our annual leave policy?",
  "top_k": 5,
  "history_max_messages": 20
}
```

The assistant response will include `sources` and should cite sources inline like `[doc:<id>#<chunk_index>]`.

## Common issues

- `DisallowedHost` error (HTML page) when calling the API (often from Streamlit container):
  - Add `ALLOWED_HOSTS=localhost,127.0.0.1,backend` to `.env`, or keep `DEBUG=1` (dev default includes `backend`).
- `401 Unauthorized` when calling protected endpoints:
  - You forgot Swagger **Authorize** or your token expired.
- Document upload returns `400 Bad Request`:
  - In Swagger, make sure you used multipart upload with the `file` field (not a JSON body).
- You can upload, but list/search shows no results:
  - Make sure Celery is running (`celery_worker` service) and wait a few seconds for processing.
