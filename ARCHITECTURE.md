# Task 1 — Scalable GitHub Data Aggregation System Architecture

**Designed by:** Sarthak Soni | GSoC 2026 Pre-Task | C2SI WebiU

---

## Overview

This document describes a scalable architecture for aggregating data from 300+ GitHub repositories and serving it efficiently to a website, while minimizing API usage and ensuring real-time updates.

---

## Architecture Diagram
```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Angular)                       │
│                    WebiU Web Application                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP Requests
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (NestJS)                          │
│         REST + GraphQL endpoints | Rate limiting | Auth          │
└──────────┬──────────────────────────────┬───────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐      ┌──────────────────────────────────┐
│   CACHE LAYER        │      │      PROCESSING LAYER             │
│   Redis              │      │   TechStackDetector               │
│   • Response cache   │      │   ActivityScorer                  │
│   • Rate limit store │      │   DataNormalizer                  │
│   • Session store    │      │   WebhookProcessor                │
└──────────────────────┘      └──────────┬─────────────────────── ┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                                │
│              PostgreSQL (persistent data)                        │
│   repositories | contributors | languages | tech_stacks         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATA INGESTION LAYER                           │
│         GitHub API Client | Webhook Receiver                     │
│         Queue (Bull/Redis) | Scheduler (cron)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  GitHub API  │
                    │  REST + GQL  │
                    └──────────────┘
```

---

## Core Components

### 1. Data Ingestion Layer
Responsible for collecting raw data from GitHub. Uses two mechanisms:
- **GitHub Webhooks** — receives push events, PR events, and release events in real time
- **Scheduled Jobs** — cron-based polling for repos without webhooks (fallback)
- **Bull Queue** — job queue to process ingestion tasks asynchronously, preventing API flooding

### 2. Processing Layer
Transforms raw GitHub data into enriched, structured records:
- **DataNormalizer** — standardizes field names, handles nulls, strips unnecessary fields
- **TechStackDetector** — analyzes manifest files to detect technologies automatically
- **ActivityScorer** — computes activity scores based on commits, stars, issues
- **WebhookProcessor** — handles incoming webhook payloads and triggers targeted updates

### 3. Storage Layer
PostgreSQL stores persistent, structured data:
- `repositories` — id, name, description, stars, forks, language, pushed_at, tech_stack
- `contributors` — login, avatar_url, contributions, repo associations
- `languages` — repo_id, language, bytes
- `tech_stacks` — repo_id, technologies[], detected_at, pushed_at_snapshot

### 4. Cache Layer (Redis)
Two-tier caching:
- **L1 — In-memory** (NestJS CacheService) — ultra-fast, short TTL (5 min), for hot endpoints
- **L2 — Redis** — shared across instances, longer TTL (1 hour), for expensive queries

Cache keys use `org:repo:pushed_at` so stale data is never served after a push event.

### 5. API Layer (NestJS)
Serves data to the frontend:
- REST endpoints for projects, contributors, tech stacks
- GraphQL for flexible querying
- Rate limiting per IP using Redis
- JWT authentication for admin endpoints

---

## Rate Limit Handling

GitHub allows 5,000 requests/hour with authentication. Strategies:

1. **Cache-first** — always check cache before hitting GitHub API
2. **Conditional requests** — use ETags and `If-None-Match` headers to avoid re-fetching unchanged data
3. **Webhook-driven updates** — only fetch data when GitHub notifies us of a change
4. **Request batching** — use GraphQL to fetch multiple repos in one request
5. **Queue throttling** — Bull queue limits concurrent GitHub API calls to 10/minute
6. **Rate limit monitoring** — check `X-RateLimit-Remaining` header; pause queue if < 100 remaining

---

## Update Mechanism

**Primary: GitHub Webhooks**
- Register webhook on the organization for `push`, `pull_request`, `create`, `delete` events
- On event receipt, queue a targeted update job for only the affected repository
- Latency: < 5 seconds from push to updated data

**Fallback: Scheduled Polling**
- For repos where webhooks cannot be configured
- Incremental polling: check `pushed_at` timestamp, only fetch full data if changed
- Schedule: every 15 minutes for active repos, every 6 hours for inactive repos

---

## Data Storage Strategy

**Stored persistently (PostgreSQL):**
- Repository metadata (name, description, stars, forks, language, topics)
- Contributor lists and contribution counts
- Detected tech stacks (expensive to compute, cache indefinitely until repo updates)
- Historical activity snapshots

**Fetched dynamically (no storage):**
- Real-time commit counts for the last 24 hours
- Live PR status
- Current rate limit status

---

## Scalability Plan (300 → 10,000 repos)

| Scale | Strategy |
|-------|----------|
| 300 repos | Single NestJS instance, in-memory cache, GitHub REST API |
| 1,000 repos | Add Redis, PostgreSQL, webhook-driven updates |
| 5,000 repos | Horizontal scaling (multiple NestJS instances), load balancer, GraphQL batching |
| 10,000 repos | Microservices (ingestion service separate from API service), message broker (Kafka/RabbitMQ), read replicas for PostgreSQL |

Key scaling techniques:
- **Stateless API servers** — any instance can handle any request
- **Database read replicas** — separate read and write workloads
- **CDN caching** — static project data cached at edge
- **GraphQL batching** — fetch 100 repos per request instead of 1

---

## Performance Optimization

1. **Paginated responses** — never return all 300 repos at once; paginate at 20/page
2. **Partial responses** — GraphQL lets frontend request only needed fields
3. **Compression** — GZIP all API responses (already implemented in WebiU via compression middleware)
4. **ETags** — browser caches responses, only re-fetches when data changes
5. **Lazy loading** — contributor avatars and repo details loaded on demand

---

## Failure Handling

| Failure | Strategy |
|---------|----------|
| GitHub API down | Serve stale cached data with a `stale: true` flag |
| Rate limit exhausted | Pause ingestion queue, serve from cache, alert admin |
| Repository deleted/private | Mark as inactive in DB, remove from frontend |
| Webhook delivery failure | GitHub retries webhooks for 72 hours; fallback polling covers the gap |
| Database unavailable | Redis cache continues serving responses for TTL duration |

---

## API Flow
```
Frontend Request
      │
      ▼
NestJS API Layer
      │
      ├─ Check Redis Cache ──► Cache HIT? ──► Return cached response
      │
      └─ Cache MISS?
            │
            ▼
      Query PostgreSQL
            │
            ├─ Data fresh (pushed_at unchanged)? ──► Return + refresh cache
            │
            └─ Data stale?
                  │
                  ▼
            Queue GitHub API fetch
                  │
                  ▼
            Update PostgreSQL + Cache
                  │
                  ▼
            Return updated response
```

---

## Technology Choices

| Component | Technology | Justification |
|-----------|------------|---------------|
| Backend | NestJS (TypeScript) | Already used in WebiU; modular, testable, production-ready |
| Database | PostgreSQL | Relational data fits repo/contributor relationships; better than MongoDB for structured queries |
| Cache | Redis | Industry standard; supports TTL, pub/sub for webhook events, and rate limit counters |
| Queue | Bull (Redis-backed) | Native NestJS integration; reliable job processing with retries |
| API | REST + GraphQL | REST for simplicity; GraphQL for flexible frontend queries and batching |
| Frontend | Angular | Already used in WebiU |
| Deployment | Docker + docker-compose | Already configured in WebiU; easy horizontal scaling |

---

## Assumptions & Limitations

- Assumes GitHub webhooks can be registered on the organization (admin access required)
- For organizations without webhook access, polling introduces up to 15-minute data lag
- Tech stack detection accuracy depends on presence of standard manifest files
- GitHub GraphQL API has a separate rate limit (5,000 points/hour) that must be monitored independently