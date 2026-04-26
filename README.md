# Algo Trading Bot

A Dockerized algorithmic trading project with:

- a Python/FastAPI trading backend
- an Interactive Brokers Gateway container
- a React frontend served by Nginx

## Quick Start

Choose one path:

1. Docker/Nginx (recommended)
   - Configure credentials in [.env](.env) using [Environment Variables](#environment-variables)
   - Start services with [Run with Docker Compose](#run-with-docker-compose)
   - Open [http://localhost](http://localhost)

2. Local development
   - Start backend API from project root:
     - `python src/main.py`
   - Start frontend dev server:
     - `cd frontend && npm install && npm run dev`
   - Open `http://localhost:5173`

Frontend-specific details are in [frontend/README.md](frontend/README.md).

## Architecture

The stack is orchestrated with Docker Compose.

- `frontend` (Nginx + built React app)
  - Exposes `http://localhost` on host port `80`
  - Serves static frontend assets
  - Reverse proxies API calls from `/api/*` to `trading-bot:8000/api/*`
- `trading-bot` (Python app)
  - Runs FastAPI on port `8000` inside Docker network
  - Not exposed directly to host
- `ib-gateway`
  - Exposes host port `4004` for IBKR connectivity

Request flow:

1. Browser calls `http://localhost`
2. Nginx serves frontend assets
3. Frontend calls `/api/...`
4. Nginx proxies `/api/...` to `trading-bot:8000/api/...`

## Repository Structure

- [docker-compose.yml](docker-compose.yml): Service orchestration
- [Dockerfile](Dockerfile): Backend container image
- [frontend/Dockerfile](frontend/Dockerfile): Frontend multi-stage image build
- [frontend/nginx.conf](frontend/nginx.conf): Nginx SPA + reverse proxy config

## Prerequisites

- Docker
- Docker Compose (plugin)
- IBKR paper/live credentials
- GROQ API key

## Environment Variables

Create a root `.env` file (do not commit secrets) with:

```env
IBKR_USER=your_ibkr_username
IBKR_PASSWORD=your_ibkr_password
GROQ_API_KEY=your_groq_api_key
```

## Run with Docker Compose

From the project root:

```bash
docker compose up --build -d
```

Check running services:

```bash
docker compose ps
```

Follow logs:

```bash
docker compose logs -f frontend trading-bot ib-gateway
```

## Access

- Frontend: `http://localhost`
- API (through Nginx):
  - `http://localhost/api/status`
  - `http://localhost/api/ledger`
  - `http://localhost/api/logs`

Note: The backend is intentionally not published on host port `8000`. API access should go through the frontend Nginx reverse proxy.

## Stop and Cleanup

Stop containers:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```

## Development Notes

If you run the frontend locally with Vite (`npm run dev`), it is separate from the Nginx production path used in Docker.
The Dockerized deployment path for frontend is:

1. build React app (`npm run build` in image build stage)
2. serve `dist` with Nginx
3. proxy `/api/` to `trading-bot`
