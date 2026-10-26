# AI CCTV Monitoring System — Backend (FastAPI)

Backend for the 5-page Flutter app: Login, Home Dashboard, Live Feed,
Evidence Log, and Analytics. Implements the "3. API & LOGIC" and
"3. PERSISTENCE LAYER" blocks from the architecture diagram.

## What's here

| File | Responsibility |
|---|---|
| `app/security.py` | Argon2id password hashing, JWT access/refresh tokens |
| `app/crypto_clips.py` | AES-256-GCM encrypt/decrypt for evidence clips |
| `app/models.py` | `User`, `Event` (evidence log), `DeviceHeartbeat` |
| `app/routers/auth.py` | `/auth/login`, `/auth/refresh`, `/auth/users` |
| `app/routers/dashboard.py` | `/dashboard` — Home page data |
| `app/routers/live_feed.py` | `/live/token` — short-lived WebRTC/go2rtc auth token |
| `app/routers/events.py` | `/events`, `/events/{id}/clip` — Evidence Log page |
| `app/routers/analytics.py` | `/analytics` — hourly traffic-flow charts |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set a real secret before running anything beyond local dev:
export JWT_SECRET_KEY=$(openssl rand -hex 32)

# Create the first admin account (all other users are created via
# POST /auth/users, which itself requires an admin JWT)
python seed_admin.py admin "ChangeMe123!" admin@example.com

uvicorn app.main:app --reload
```

Interactive API docs at `http://localhost:8000/docs`.

### Pointing at TimescaleDB instead of the local SQLite default

```bash
export DATABASE_URL="postgresql+psycopg2://user:password@db-host:5432/cctv"
pip install psycopg2-binary
```

## Auth flow (matches the "Secure Login Page" spec)

1. Flutter app posts `{username, password}` to `POST /auth/login` over
   HTTPS (TLS 1.3 terminated at your reverse proxy / uvicorn `--ssl-*` flags —
   this app assumes it's always reached over TLS in production).
2. Server verifies the password against the stored **Argon2id** hash.
3. On success, returns a JWT `access_token` (short-lived, 30 min default)
   and `refresh_token` (7 days default). Failed attempts are tracked and
   the account temporarily locks after 5 failures.
4. Every other endpoint requires `Authorization: Bearer <access_token>`.
   When the access token expires, call `POST /auth/refresh` with the
   refresh token to get a new pair without re-prompting for a password.

## Endpoint summary

```
POST /auth/login              -> {access_token, refresh_token}
POST /auth/refresh             -> new token pair
POST /auth/users   [admin]     -> create a new personnel account

GET  /dashboard                -> thumbnail url, quick stats, Pi heartbeat status

GET  /live/token                -> short-lived token + go2rtc WebRTC URL

GET  /events?category=traffic  -> list evidence log entries (filterable)
GET  /events/{id}/clip          -> decrypts clip server-side, streams MP4

GET  /analytics?date=YYYY-MM-DD -> hourly vehicle flow, peak hour
```

## Notes / next steps

- **TLS**: run behind nginx/Caddy with TLS 1.3, or pass `--ssl-keyfile`/
  `--ssl-certfile` to uvicorn directly.
- **Clip encryption key**: `app/crypto_clips.py` derives a placeholder
  key from `JWT_SECRET_KEY` so the project runs out of the box. Replace
  with a key from a proper secrets manager (AWS KMS / Vault) before
  storing real evidence.
- **Populating events**: this backend exposes the read/playback side.
  The write side (YOLOv8 + MediaPipe pipeline calling `encrypt_clip()`
  and inserting `Event` rows) lives in the AI processing service — wire
  it to call into this same DB/models.
- **MQTT heartbeat**: `DeviceHeartbeat` rows should be upserted by a
  small MQTT subscriber process listening to the Pi's heartbeat topic;
  `/dashboard` just reads the latest row.
- Migrations: swap `Base.metadata.create_all()` for Alembic once the
  schema stabilizes.
