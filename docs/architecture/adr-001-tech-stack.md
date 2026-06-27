# ADR-001: Technology Stack Selection
**Date:** 2026-06-06 | **Status:** Accepted (Database row amended — see ADR-004) | **Author:** @solution-architect

> **Amendment (2026-06-24):** The database is now **PostgreSQL** (driver:
> psycopg 3, `postgresql+psycopg://`) with **schema-per-school** multi-tenancy.
> The "SQLite3 (dev) → PostgreSQL (prod)" plan below has been executed; SQLite
> now only backs the in-memory unit-test suite. See
> [ADR-004](adr-004-postgresql-schema-per-school.md).

## Context
We need to select a technology stack for the School Management System that balances:
- Developer productivity (small team)
- Rapid feature delivery
- Long-term maintainability
- Hosting cost (school budget is limited)

## Decision
| Layer | Choice | Rejected Alternatives |
|-------|--------|----------------------|
| Backend | Python Flask 3.x | Django (too opinionated), FastAPI (less ecosystem for admin tasks), Node.js/Express |
| ORM | SQLAlchemy 2.x | Raw SQL (hard to migrate later), Django ORM (ties to Django) |
| Database | PostgreSQL (schema-per-school); SQLite for unit tests | MySQL (licence concerns), MongoDB (relational data doesn't fit document model) |
| DB Driver | psycopg 3 (`psycopg[binary]`) | psycopg2 (no Python 3.14 wheels) |
| Frontend | Angular 17+ | React (less opinionated, more boilerplate), Vue (smaller ecosystem for enterprise) |
| UI Library | PrimeNG | Angular Material (fewer components), Ng-Zorro (less community) |
| Auth | JWT (Flask-JWT-Extended) | Session cookies (stateful, harder to scale), OAuth only (overkill for internal app) |

## Consequences
**Benefits:**
- Flask's simplicity means less boilerplate; faster to prototype
- SQLAlchemy abstracts DB engine — switching SQLite→PostgreSQL requires zero code changes
- Angular's strict typing + PrimeNG's rich component set delivers enterprise UI quickly
- JWT is stateless — easy horizontal scaling later

**Risks:**
- ~~SQLite has write-locking in concurrent scenarios~~ — **resolved**: migrated to PostgreSQL (MVCC) with schema-per-school (ADR-004)
- Flask has no built-in admin — we build our own (this is intended)
- Angular bundle size can grow — mitigated by lazy-loaded modules
