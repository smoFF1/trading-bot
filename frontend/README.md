# Frontend (React + Vite)

This directory contains the React dashboard for the Algo Trading Bot.

## Docker and Nginx Deployment

In Dockerized environments, this frontend is:

- built with [frontend/Dockerfile](Dockerfile)
- served by Nginx with [frontend/nginx.conf](nginx.conf)
- exposed on `http://localhost` by the `frontend` service in [docker-compose.yml](../docker-compose.yml)
- reverse-proxied to backend API through `/api/*`

For full stack setup, environment variables, and Compose commands, see the root documentation: [README.md](../README.md).

## Local Development

Run the frontend locally with Vite:

```bash
cd frontend
npm install
npm run dev
```

Vite dev server defaults to `http://localhost:5173`.

API calls to `/api/*` are proxied by [frontend/vite.config.js](vite.config.js) to `http://127.0.0.1:8000`, so make sure the backend API is running when developing locally.

## Build

To generate a production build:

```bash
npm run build
```

Output is written to `dist/` and used by Nginx in containerized deployment.
