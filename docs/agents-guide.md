# SMS Agent Team — Quick Reference

Invoke any agent by starting your message with their trigger keyword.

---

## @product-owner
**When to use:** Defining features, writing user stories, prioritizing backlog, making product decisions.
Owns the Product Backlog and decides WHAT to build. Go here first when starting any new feature or module.

---

## @solution-architect
**When to use:** System design, API contracts, technology decisions, cross-module integration questions.
Owns the technical vision and makes final calls on architecture, coding standards, and design trade-offs.

---

## @scrum-master
**When to use:** Sprint planning, standups, reviews, retrospectives, tracking velocity, clearing blockers.
Facilitates Scrum ceremonies and protects the team from scope creep. Run sprint ceremonies through this agent.

---

## @backend-engineer
**When to use:** Flask routes, services, SQLAlchemy models, JWT auth, RBAC, API logic.
Implements the REST API and business logic layer. No raw SQL — ORM only. No logic in routes — services only.

---

## @frontend-engineer
**When to use:** Angular components, PrimeNG UI, routing, guards, interceptors, reactive forms.
Builds Angular standalone components with PrimeNG. Uses signals, lazy loading, and functional guards.

---

## @database-engineer
**When to use:** Schema design, migrations, model relationships, query optimization.
Designs the database schema and manages Flask-Migrate (Alembic) migrations. Owns data modeling decisions.

---

## @devops-engineer
**When to use:** Docker, GitHub Actions CI/CD, environment config, deployment pipelines.
Sets up containerization and automates build/test/deploy workflows across dev, staging, and production.

---

## @github-agent
**When to use:** Branch protection rules, repo settings, team access, labels, milestones, PR templates.
Manages GitHub repository administration and enforces the `feature → develop → main` branching workflow.

---

## @qa-engineer
**When to use:** Writing tests, test plans, coverage reports, bug reports, edge case reviews.
Writes pytest (backend) and Angular (frontend) test suites. Maintains 80%+ coverage requirement.

---

## @security-engineer
**When to use:** Security reviews, OWASP audits, JWT/RBAC checks, dependency vulnerability scans.
Reviews code touching auth and sensitive data. Enforces security standards before any PR merges to main.

---

## Quick Decision Guide

| I want to... | Use this agent |
|---|---|
| Add a new feature to the backlog | `@product-owner` |
| Design how a new module fits together | `@solution-architect` |
| Plan the next sprint | `@scrum-master` |
| Build a new API endpoint | `@backend-engineer` |
| Build a new UI page or component | `@frontend-engineer` |
| Add a new database table or column | `@database-engineer` |
| Set up Docker or CI/CD | `@devops-engineer` |
| Manage repo branches or permissions | `@github-agent` |
| Write or fix tests | `@qa-engineer` |
| Review code for security issues | `@security-engineer` |
