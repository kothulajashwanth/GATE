# Developer Guide - ExamShield AI

## Quick Start

```bash
# Clone and install
git clone <repo>
cd examshield-ai
pnpm install

# Start infrastructure
docker compose -f docker/docker-compose.yml up -d postgres redis

# Configure env
cp .env.example .env
# Edit .env with your keys

# Backend
cd apps/api
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# Frontend (separate terminal)
cd apps/web
pnpm dev
```

## Project Structure

```
examshield-ai/
├── apps/
│   ├── web/          # Next.js 16 frontend
│   └── api/          # FastAPI backend
├── packages/
│   ├── ui/           # shadcn/ui components
│   ├── types/        # Shared TypeScript types
│   └── utils/        # Shared utilities
├── database/         # ER diagrams, SQL scripts
├── docs/             # Architecture, deployment, manuals
├── docker/           # Docker compose, Dockerfiles
└── scripts/          # CI/CD, migration helpers
```

## Key Patterns

### Repository Pattern
```
services/           # Business logic
  ├─ repositories/  # Data access (BaseRepository, UserRepository, etc.)
  ├─ ai.py          # AI provider abstraction
  ├─ results.py     # Result calculation
  └─ imports.py     # Excel import with validation
```

### API Layer
```
api/
  ├─ routes/        # REST endpoints (health, users, students, exams, questions, ai, analytics)
  ├─ deps.py        # FastAPI dependencies
  └─ router.py      # Route aggregation
```

### Database Models (SQLAlchemy 2.0)
```
models/
  ├─ base.py        # Base, TimestampMixin, SoftDeleteMixin, guid_pk()
  ├─ user.py        # User, Role enum
  ├─ academic.py    # Department, Semester, Section
  ├─ student.py     # Student profile
  ├─ question.py    # Question, QuestionVersion, Subject, Folder
  ├─ exam.py        # Exam, ExamQuestion, ExamSchedule
  ├─ session.py     # ExamSession, SessionAnswer, ViolationRecord
  ├─ result.py      # ExamResult
  ├─ audit.py       # AuditLog
  └─ notification.py # Notification
```

### Frontend Architecture
```
apps/web/
├── app/                    # Next.js App Router
│   ├── admin/              # Admin portal pages
│   ├── student/            # Student portal pages
│   └── exam/[examId]/      # Exam engine page
├── components/
│   ├── app-shell.tsx       # Shared layout
│   ├── page-header.tsx
│   ├── data-table-pagination.tsx
│   └── ui/                 # Re-exports from @examshield/ui
├── lib/
│   ├── api/                # API client + TanStack Query
│   └── constants.ts
└── providers.tsx           # QueryClient, Theme, Toaster
```

## Coding Standards

- TypeScript strict mode everywhere
- Python type hints + mypy
- Ruff for Python linting, ESLint for TS
- Prettier + prettier-plugin-tailwindcss
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## Testing

```bash
# Backend
cd apps/api
.venv/bin/pytest tests/ -q

# Frontend
cd apps/web
pnpm test

# E2E (playwright)
npx playwright test
```

## Adding a Feature

1. Define types in `packages/types/src/index.ts`
2. Add DB model in `apps/api/app/db/models/`
3. Create migration: `alembic revision --autogenerate -m "description"`
4. Add repository methods
5. Add service logic
6. Add API route
6. Build UI component
7. Write tests

## Common Commands

```bash
# Backend
cd apps/api
.venv/bin/python -m alembic revision --autogenerate -m "msg"
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m pytest tests/ -q
.venv/bin/ruff check . --fix

# Frontend
cd apps/web
pnpm dev
pnpm build
pnpm lint
pnpm format:check
```

## Debugging Tips

- Backend logs: `structlog` JSON output
- Frontend: React DevTools, TanStack Query DevTools
- Database: `docker compose exec postgres psql -U examshield -d examshield`
- Redis: `docker compose exec redis redis-cli MONITOR`