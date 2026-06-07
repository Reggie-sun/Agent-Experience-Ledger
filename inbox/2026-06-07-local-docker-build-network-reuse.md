---
schema_version: "1"
title: "Separate Docker build network faults from dependency resolver faults before optimizing reuse"
date: "2026-06-07"
source_agent: "codex"
status: "candidate"
category: "debugging"
tags: ["docker", "networking", "build-cache", "local-runtime"]
confidence: "high"
repo: "Enterprise-grade_RAG"
branch: "main"
capture_request_id: "capture-20260607-104520-019e9fed-97e6-78f1-8eb9--2cc3b388"
source_repo: "Enterprise-grade_RAG"
source_cwd: "/home/reggie/vscode_folder/Enterprise-grade_RAG"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, API key, proxy credential, or private runtime secret included."
---

## Summary

When a local Docker deployment build is slow or repeatedly failing, first classify whether the blocker is build-network routing, package-index behavior, dependency resolver metadata, or missing cache reuse. Fixing these separately avoids wasting time on blind rebuilds and makes later `docker compose build` runs predictable.

## Applies When

- A workstation-local Docker Compose stack builds Python or frontend images through flaky external package indexes.
- The host has working proxy settings, but Docker build arguments expand to empty proxy values.
- Heavy local assets such as model files, torch wheels, CUDA wheels, or base images already exist on the machine.
- `pip` or `npm ci` failures look like network slowness but are actually resolver or lockfile consistency problems.

## Evidence

- `docker-compose.local-machine.yml` was adjusted to pass explicit build proxy and `PIP_INDEX_URL` arguments, while the gitignored local runtime file provided machine-specific `DOCKER_BUILD_*` values.
- `docker/Dockerfile.local-ml` now installs a local torch wheel and local CUDA dependency wheels in a cacheable layer before installing model-service dependencies.
- The model-service build was verified to reuse all layers on a repeat build after pinning the Dockerfile frontend digest.
- A frontend Docker build that stalled on unavailable base image metadata was recovered by reusing local `node:20-alpine` and `caddy:2.8.4-alpine` images instead of pulling new `node:22-alpine` and `nginx` images.
- `frontend/package-lock.json` had to be refreshed after `npm ci` exposed a lockfile mismatch; this was a separate dependency-consistency issue, not a network issue.

## Lesson

For local runtime bring-up, run small probes before continuing expensive builds: compare host and container package-index access, inspect expanded compose build args, check available local images and wheels, and isolate resolver errors from transport errors. Prefer explicit build args, pinned Dockerfile frontends, local additional build contexts, and cacheable heavy dependency layers before retrying full-stack `up --build`.

## Avoid

- Do not assume a slow build is using the host proxy; `--env-file` performs Compose substitution but does not automatically inject all host environment into Docker build args.
- Do not keep changing package mirrors without testing real wheel downloads; a simple index page can be fast while wheel URLs return errors.
- Do not let pip resolve a locally installed nightly torch if its metadata requires an unavailable exact auxiliary package; install torch locally and make dependent packages reuse it deliberately.
- Do not pull new frontend base images when suitable local images already exist and the goal is a workstation-only deployment.

## Verification

- Check `docker compose --env-file <runtime-env> -f <compose-file> config` for non-empty build proxy and package-index values.
- Build model services once, then immediately rebuild to confirm local torch/CUDA and Python dependency layers are cached.
- Verify runtime health through both direct API endpoints and the frontend reverse proxy.
- Use a browser smoke test after frontend serving changes to confirm the SPA loads and `/api` proxying works without console errors.
