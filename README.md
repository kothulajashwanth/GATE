# ExamShield AI

Enterprise Secure Online Examination Management System for colleges. Monorepo: Next.js 16 web app + FastAPI backend + PostgreSQL + Redis.

## Quick Start

```bash
# 1. Install pnpm (>= 9) and Python (>= 3.12)
# 2. Install dependencies
pnpm install
cd apps/api && python -m venv .venv && .venv/Scripts/activate && pip install -e ".[dev]"

# 3. Start infrastructure (Postgres + Redis + MinIO)
pnpm db:up

# 4. Configure environment
cp .env.example .env                          # root
cp apps/web/.env.example apps/web/.env.local  # frontend
cp apps/api/.env.example apps/api/.env        # backend

# 5. Migrate and seed
pnpm --filter @examshield/api db:migrate
pnpm --filter @examshield/api db:seed

# 6. Run in development
pnpm dev   # web on :3000, api on :8000
```

## Monorepo Layout

```
examshield-ai/
├── apps/
│   ├── web/          # Next.js 16 frontend
│   └── api/          # FastAPI backend
├── packages/
│   ├── ui/           # shadcn/ui components
│   ├── types/        # shared TypeScript types
│   └── utils/        # shared utilities
├── database/         # SQL scripts, ER diagram
├── docs/             # Architecture, API, deployment guides
├── scripts/          # CI helpers
├── docker/           # compose files
└── .github/          # CI workflows
```

Full documentation: [`docs/README.md`](docs/README.md).
