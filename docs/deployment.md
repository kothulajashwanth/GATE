# ExamShield AI - Deployment Guide

## Overview

This guide covers deploying ExamShield AI to production infrastructure.

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │     │   Backend   │     │  Database   │
│   (Vercel)  │────▶│  (Railway)  │────▶│  (Supabase) │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Redis     │
                    │  (Railway)  │
                    └─────────────┘
```

## Prerequisites

- Vercel account
- Railway account
- Supabase account
- Clerk account (authentication)
- Resend account (email)
- OpenAI / Gemini API keys (AI features)

## Environment Variables

### Frontend (Vercel)

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
CLERK_SIGNING_SECRET=whsec_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
CLERK_WEBHOOK_SECRET=whsec_...

NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Backend (Railway)

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=your-64-char-random-secret

DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://user:pass@host:6379/0

STORAGE_PROVIDER=supabase
STORAGE_ENDPOINT=https://your-project.supabase.co/storage/v1
STORAGE_BUCKET=examshield
STORAGE_ACCESS_KEY=...
STORAGE_SECRET_KEY=...

ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

CLERK_SECRET_KEY=sk_live_...
CLERK_ISSUER=https://your-clerk-domain.clerk.accounts.dev
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json

OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
AI_PROVIDER=openai

RESEND_API_KEY=re_...
EMAIL_FROM=ExamShield <noreply@yourdomain.com>

API_INTERNAL_KEY=shared-secret-for-webhooks
ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

### Supabase

- Create project
- Run migrations via `alembic upgrade head`
- Create storage bucket `examshield`
- Configure RLS policies if needed

## Deployment Steps

### 1. Database (Supabase)

```bash
# Locally, point to Supabase
export DATABASE_URL="postgresql+asyncpg://postgres:password@db.xxx.supabase.co:5432/postgres"
cd apps/api
alembic upgrade head
```

### 2. Backend (Railway)

1. Create new Railway project
2. Add PostgreSQL and Redis services
3. Connect GitHub repo
4. Set root directory to `apps/api`
5. Add all environment variables
6. Deploy - Railway will run `alembic upgrade head && uvicorn app.main:app`

### 3. Frontend (Vercel)

1. Import GitHub repo
2. Set root directory to `apps/web`
3. Add environment variables
4. Deploy - Vercel detects Next.js automatically

### 4. Clerk Configuration

1. Create Clerk application
2. Add JWT template named `examshield` with claims:
   ```json
   {
     "sub": "{{user.id}}",
     "role": "{{user.public_metadata.role}}",
     "email": "{{user.primary_email_address.email_address}}",
     "name": "{{user.full_name}}"
   }
   ```
3. Configure sign-in/up URLs
4. Enable "Single session per user" in Sessions settings
5. Add webhook URL: `https://your-frontend.vercel.app/api/clerk/webhook`
6. Subscribe to `user.created`, `user.updated`, `user.deleted`

### 5. DNS & SSL

- Point `api.yourdomain.com` to Railway
- Point `yourdomain.com` to Vercel
- Both provide automatic SSL

## Health Checks

```bash
# Backend
curl https://api.yourdomain.com/api/v1/health
# {"status":"ok","version":"0.1.0","database":"up","redis":"up"}

# Frontend
curl https://yourdomain.com
```

## Monitoring

- Railway: built-in metrics, logs
- Vercel: analytics, function logs
- Supabase: database metrics, query performance
- Clerk: authentication events
- Resend: email delivery stats

## Rollback

```bash
# Railway
railway rollback

# Vercel
vercel rollback [deployment-url]

# Database (if migration failed)
alembic downgrade -1
```

## Backup

- Supabase: automatic daily backups (PITR on Pro+)
- Export critical data via admin panel: `Settings → Database → Export`

## Scaling

| Component | Scale Strategy |
|-----------|---------------|
| Backend   | Railway auto-scales workers; increase `uvicorn --workers` |
| Database  | Supabase read replicas, connection pooling (PgBouncer) |
| Redis     | Railway Redis cluster |
| Frontend  | Vercel edge network automatic |

## Security Checklist

- [ ] All env vars in secrets (not repo)
- [ ] HTTPS everywhere
- [ ] CSP headers present
- [ ] Rate limiting active
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (ORM only)
- [ ] XSS prevention (React auto-escape)
- [ ] Clerk JWT verification
- [ ] Single session enforcement
- [ ] Exam security mode tested
- [ ] Audit logging verified
- [ ] Resend domain verified