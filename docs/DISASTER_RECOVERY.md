# GATE IGNITE - Disaster Recovery & Incident Response Guide

## 1. Overview & Operational Principles

This document outlines the disaster recovery (DR) procedures and emergency protocols for the **GATE IGNITE Examination Platform**.

### Critical System Assets
- **Frontend Application**: Next.js / TypeScript hosted on Vercel (`https://fabgate.vercel.app`).
- **Backend API Service**: FastAPI / Python hosted on Render.
- **Database Engine**: Render PostgreSQL managed database instance.
- **Authentication Infrastructure**: Clerk Authentication Provider.

---

## 2. Disaster Scenarios & Recovery Workflows

### Scenario A: Database Outage or Data Corruption
- **Detection**: Health endpoint `/health/database` returns HTTP 503 Service Unavailable or database connection times out.
- **Immediate Response**:
  1. Freeze active examination sessions to prevent partial answer loss.
  2. Verify Render PostgreSQL service status.
- **Recovery Procedure**:
  1. Access Render Database Dashboard -> Backups tab.
  2. Select the latest clean point-in-time snapshot prior to corruption.
  3. Execute point-in-time restore to a new database instance.
  4. Update `DATABASE_URL` environment variable in Render API environment.
  5. Trigger zero-downtime redeployment of FastAPI backend.
  6. Run `/health/database` to confirm reconnection.

### Scenario B: Backend Service Outage (FastAPI / Render)
- **Detection**: API requests return HTTP 502/504 Bad Gateway or health check `/health` fails.
- **Recovery Procedure**:
  1. Check Render deployment logs for container crash tracebacks.
  2. If caused by a bad code release: trigger single-click Rollback in Render Dashboard to previous green release build.
  3. If caused by high load: scale Render instance memory/CPU.
  4. Verify recovery via `/health`.

### Scenario C: Frontend Service Outage (Next.js / Vercel)
- **Detection**: Vercel deployment error or HTTP 500 on student/admin web portal.
- **Recovery Procedure**:
  1. Open Vercel Project Dashboard -> Deployments tab.
  2. Promote the latest verified deployment build to Production.
  3. Clear Vercel Edge CDN cache.

### Scenario D: Credential Compromise & Key Rotation
- **Immediate Action**:
  1. If `DATABASE_URL` password is compromised: Reset PostgreSQL password in Render and immediately update environment variable.
  2. If `CLERK_SECRET_KEY` is compromised: Generate a new secret key in Clerk Dashboard and update backend environment.
  3. If `OPENAI_API_KEY` or `GEMINI_API_KEY` is compromised: Revoke old keys in vendor developer portals, issue new keys, and update Render environment settings.

---

## 3. Incident Communication & Post-Mortem

- **Notification**: Inform college administration and affected students via institutional email.
- **Post-Mortem**: Document root cause, timeline of events, downtime duration, data loss assessment, and preventive action items within 48 hours of resolution.
