# TaskMate AI Monorepo

TaskMate AI is a Docker-first monorepo bundling the core user workspace, an administrative control plane, and all infrastructure dependencies required for production deployments.

## Stack

- **Backend**: FastAPI, JWT authentication with role-based access control (RBAC), Celery for async jobs, Redis broker, Telegram bot integration, PostgreSQL persistence.
- **Frontend**: Next.js 14 App Router, TailwindCSS, multi-lingual (English, Persian, Arabic) with runtime locale detection and RTL support.
- **Admin Panel**: React 18 (Vite), TailwindCSS, Chart.js & Recharts powered dashboards, JWT protected sign-in flow.
- **Reverse Proxy**: Hardened Nginx gateway fronting all services.

## Getting Started

1. Duplicate `.env.example` to `.env` and adjust secrets:

   ```bash
   cp .env.example .env
   ```

2. Bring the full stack online:

   ```bash
   docker-compose up -d --build
   ```

3. Access the services:

   - API: `http://localhost/api/v1` (proxied through Nginx)
   - Frontend: `http://localhost`
   - Admin panel: `http://localhost/admin`

4. Health check: `GET http://localhost/healthz`

### Creating the first admin user

1. Ensure the database container is running and migrations have been applied:

   ```bash
   docker compose up -d
   docker compose exec backend alembic upgrade head
   ```

2. Generate a password hash inside the backend container (replace `SuperSecret123` with your desired password—bcrypt only accepts the first 72 bytes, so pick something shorter than that limit):

   ```bash
   docker compose exec backend python -c "from backend.core.security import hash_password; print(hash_password('SuperSecret123'))"
   ```

   Copy the resulting hash value from the command output.

   > **Tip:** If you prefer a longer passphrase, truncate it before hashing (for example `print(hash_password('my passphrase'[:72]))`) so the bcrypt handler accepts it.

3. Insert the admin user into PostgreSQL, substituting your username and the copied hash:

   ```bash
   docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
     -c "INSERT INTO admin_users (username, password_hash) VALUES ('admin', 'PASTE_HASH_HERE');"
   ```

You can now sign in to the admin panel at `http://localhost/admin` using the username you inserted and the original password from step 2.

## Services

| Service   | Port | Description |
|-----------|------|-------------|
| backend   | 8000 | FastAPI app + Celery worker entrypoint |
| frontend  | 3000 | Next.js locale-aware client |
| admin     | 4173 | React admin console |
| db        | 5432 | PostgreSQL 15 |
| redis     | 6379 | Redis 7 cache/broker |
| nginx     | 80/443 | Reverse proxy and SSL terminator |

All services are networked on the `taskmate` bridge network to simplify service discovery inside Docker.

## Backend Tips

- Celery workers can be scaled by adding a `celery` service referencing `backend/app/worker.py` if you require dedicated processing containers.
- Telegram bot execution is optional. Provide `TELEGRAM_TOKEN` to enable real message polling inside the backend container.

## Frontend Locales

The frontend auto-detects locale through middleware and supports English (`/en`), Persian (`/fa`), and Arabic (`/ar`). RTL layout is automatically enforced for Persian and Arabic locales.

## Production Notes

- Supply TLS certificates to `nginx` by mounting files into the `nginx_certs` volume. During local development, the HTTPS server simply redirects to HTTP.
- Override environment variables via Docker Compose or a secrets manager as needed for deployment targets.
- Configure nightly database backups by mounting the repository's `ops/nightly_postgres_backup.sh` script into a cron job or scheduled task. Set `POSTGRES_DSN`, `BACKUP_DIR`, and optional `RETENTION_DAYS` so the script can emit compressed dumps and prune anything older than the retention window.

## Production Deployment

1. Install Docker Engine and Docker Compose on the host (Ubuntu example):

   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose
   sudo systemctl enable --now docker
   ```

2. Clone the repository and move into it:

   ```bash
   git clone https://github.com/your-org/taskmate-ai.git
   cd taskmate-ai
   ```

3. Copy the environment template and provide the required secrets:

   ```bash
   cp .env.example .env
   # edit .env to fill in API keys, JWT secrets, database DSN, etc.
   ```

4. Build and start the full stack:

   ```bash
   docker-compose up -d --build
   ```

5. Configure Nginx virtual hosts (`nginx/nginx.conf`) to map domains:

   - `taskmate.ai` → frontend service
   - `api.taskmate.ai` → backend service
   - `panel.taskmate.ai` → admin-panel service

   Reload the running container after adjustments:

   ```bash
   docker-compose exec nginx nginx -s reload
   ```

6. Provision TLS certificates using one of the following approaches:

   - **Certbot** (Let's Encrypt): mount `/etc/letsencrypt` into the nginx container, run `certbot certonly --webroot -w /var/www/html -d taskmate.ai -d api.taskmate.ai -d panel.taskmate.ai`, and reference the issued certificates inside `nginx/nginx.conf`.
   - **Caddy**: alternatively, replace the nginx service with a Caddy container configured for automatic HTTPS (see <https://caddyserver.com/docs/quick-starts/reverse-proxy> for reference).

7. Register the Telegram webhook so the bot receives updates:

   ```bash
   curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
     -d "url=https://api.taskmate.ai/telegram/webhook/<secret>"
   ```

8. Validate the deployment by hitting the health endpoint:

   ```bash
   curl https://taskmate.ai/healthz
   ```
