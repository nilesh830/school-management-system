# ADR-001: Technology Stack Selection
**Date:** 2026-06-06 | **Status:** Accepted | **Author:** @solution-architect

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
| Database | SQLite3 (dev) → PostgreSQL (prod) | MySQL (licence concerns), MongoDB (relational data doesn't fit document model) |
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
- SQLite has write-locking in concurrent scenarios — mitigated by migrating to PostgreSQL before production
- Flask has no built-in admin — we build our own (this is intended)
- Angular bundle size can grow — mitigated by lazy-loaded modules
