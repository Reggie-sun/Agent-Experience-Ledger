---
schema_version: "1"
title: "Bind direct host ports to loopback when Cloudflare Tunnel is the public entry"
date: "2026-06-07"
source_agent: "codex"
status: "candidate"
category: "deployment"
tags: ["cloudflare", "docker-compose", "networking", "security"]
confidence: "high"
repo: "Enterprise-grade_RAG"
branch: "main"
capture_request_id: "capture-20260607-092054-019ea158-1903-7363-9749--a6a68511"
source_repo: "Enterprise-grade_RAG"
source_cwd: "/home/reggie/vscode_folder/Enterprise-grade_RAG"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, token, .env value, or customer data included."
---

## Summary

When adding Cloudflare Tunnel to a Docker Compose app, keep the application as a same-network origin for `cloudflared` and bind any direct host debug port to `127.0.0.1` by default. This preserves local troubleshooting access without creating a public bypass around Cloudflare, WAF, Access policy, or Tunnel routing.

## Applies When

- Adding `cloudflared` to an existing Docker Compose topology.
- Serving a frontend container that proxies `/api/` to an internal API service.
- The intended public hostname should enter through Cloudflare Tunnel, not through exposed host ports.

## Evidence

- `docker-compose.local-machine.yml` added `frontend` and `cloudflared` services under a `cloudflare` profile.
- `frontend/nginx.conf` serves the Vite build on container port `8080` and proxies `/api/` to `api:8020` over Compose DNS.
- The direct frontend host mapping was tightened to `${FRONTEND_PUBLIC_BIND:-127.0.0.1}:${FRONTEND_PUBLIC_PORT:-3000}:8080`.
- Validation included `CLOUDFLARE_TUNNEL_TOKEN=dummy docker compose -f docker-compose.local-machine.yml --profile local-infra --profile local-worker --profile cloudflare config --services` and `cd frontend && npm run build`.

## Lesson

For Tunnel-based public deployment, model Cloudflare as the only public ingress and make the origin URL an internal service address such as `http://frontend:8080`. If a host port is kept for diagnostics, default it to loopback and document how to intentionally widen it.

## Avoid

- Mapping frontend/API ports to all interfaces by default when Cloudflare Tunnel is supposed to be the public boundary.
- Publishing databases, vector stores, queues, workers, or OCR services as Tunnel public hostnames unless there is a deliberate access design.
- Committing real Tunnel tokens; use local `.env` or a secret store.

## Verification

- Check `docker compose ... config` to ensure the Tunnel profile resolves the intended services.
- Inspect the rendered port mapping and confirm direct host access binds to `127.0.0.1` unless explicitly overridden.
- Build the frontend and confirm browser API calls remain same-origin `/api/...` behind the frontend reverse proxy.
