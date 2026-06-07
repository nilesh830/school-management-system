# School Management System (SMS) — Project Guide

## Project Overview
A full-stack School Management System built with:
- **Backend:** Python Flask 3.x + SQLAlchemy + Flask-JWT-Extended
- **Database:** SQLite3 (via SQLAlchemy — PostgreSQL-compatible)
- **Frontend:** Angular 17+ + PrimeNG + PrimeFlex
- **Auth:** JWT (access token 15min, refresh 7 days)
- **API Style:** RESTful JSON with standard envelope response

## Agent Team
Invoke these specialized agents by starting a message with their role:

| Agent | Trigger | Responsibility |
|-------|---------|----------------|
| `@product-owner` | Requirements, user stories, backlog | Defines WHAT to build |
| `@solution-architect` | Design decisions, API contracts | Defines HOW it fits together |
| `@scrum-master` | Sprint planning, ceremonies | Keeps team on track |
| `@backend-engineer` | Flask routes, services, models | Python API development |
| `@frontend-engineer` | Angular components, PrimeNG UI | Angular SPA development |
| `@database-engineer` | Schema, migrations, queries | Data modeling |
| `@devops-engineer` | Docker, CI/CD, GitHub Actions | Infrastructure |
| `@github-agent` | Repo setup, access, branches | GitHub administration |
| `@qa-engineer` | Tests, bug reports, coverage | Quality assurance |
| `@security-engineer` | Security reviews, OWASP | Vulnerability prevention |

## Directory Structure
```
SMS/
├── .claude/agents/          # Specialized agent definitions
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── routes/          # Flask blueprints (one per module)
│   │   ├── services/        # Business logic layer
│   │   └── utils/           # Response formatter, decorators
│   ├── tests/               # pytest test suite
│   ├── config.py
│   ├── run.py
│   └── requirements.txt
├── frontend/
│   └── src/app/
│       ├── core/            # Guards, interceptors, auth
│       ├── shared/          # Reusable components
│       └── modules/         # Lazy-loaded feature modules
├── database/
│   ├── migrations/          # Flask-Migrate Alembic files
│   └── seeds/               # Development seed data
├── docs/
│   ├── architecture/        # ADRs and system diagrams
│   ├── api/                 # API documentation
│   └── sprints/             # Sprint plans and retrospectives
└── .github/workflows/       # GitHub Actions CI/CD
```

## API Standards
- Base URL: `/api/v1/`
- Auth header: `Authorization: Bearer <JWT>`
- Response envelope:
  ```json
  { "success": true, "data": {}, "message": "...", "errors": null }
  ```
- Pagination: `?page=1&per_page=20`

## RBAC Roles (Hierarchy)
`Admin > Teacher > Student > Parent`

## Core Modules
1. Authentication & Authorization
2. Student Management
3. Teacher Management
4. Class & Section Management
5. Attendance Management
6. Grade & Exam Management
7. Fee Management
8. Communication (Announcements)
9. Library Management
10. Transport Management
11. Reports & Analytics
12. **Parent Portal** ← bridges school ↔ student ↔ parent

## Parent Portal — Key Architecture Points
The Parent Portal is a **dedicated, mobile-first interface** for parents/guardians within the same Angular SPA. It is NOT the admin panel — it has its own layout, navigation, and API namespace.

### Parent Portal URLs
| Frontend Route | Description |
|----------------|-------------|
| `/parent/dashboard` | Overview of all linked children |
| `/parent/children/:id/attendance` | Child attendance calendar |
| `/parent/children/:id/grades` | Exam results & report cards |
| `/parent/children/:id/fees` | Fee status & payment history |
| `/parent/leave-applications` | Submit & track leave requests |
| `/parent/messages` | Parent-Teacher messaging |
| `/parent/notices` | School announcements |
| `/parent/profile` | Parent profile management |

### Parent Portal API
Base: `/api/v1/parent-portal/*` — all require `role=parent` in JWT.
Data isolation enforced at **service layer** via `student_parent` join table — parents can only see their own children.

### New Models (Parent Portal)
- [backend/app/models/parent.py](backend/app/models/parent.py) — `Parent` + `student_parent` association
- [backend/app/models/leave_application.py](backend/app/models/leave_application.py) — Leave requests
- [backend/app/models/notification.py](backend/app/models/notification.py) — In-app notifications
- [backend/app/models/parent_message.py](backend/app/models/parent_message.py) — Parent-Teacher messaging

### New Routes (Parent Portal)
- [backend/app/routes/parent_portal.py](backend/app/routes/parent_portal.py) — Dashboard, children, attendance, grades, fees, leave, notifications

## Development Rules
- No business logic in Flask routes — use Services layer
- No raw SQL — SQLAlchemy ORM only
- All inputs validated with Marshmallow schemas
- Passwords hashed with bcrypt (never plain text)
- All routes require `@jwt_required()` or `@roles_required()`
- Angular: Reactive Forms only, lazy-loaded modules
- Tests required alongside every feature (80%+ coverage)
- No secrets committed — use .env files

## Git Workflow
```
main (prod) ← develop (staging) ← feature/SMS-xxx-description
```
- PRs to develop: 1 review required + CI passing
- PRs to main: 2 reviews required + full CI passing

## Quick Start
```bash
# Backend
cd backend && pip install -r requirements.txt
flask db upgrade
flask run

# Frontend  
cd frontend && npm install
ng serve
```
