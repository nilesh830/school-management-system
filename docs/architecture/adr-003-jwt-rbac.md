# ADR-003: JWT Claims Strategy & RBAC Design
**Date:** 2026-06-06 | **Status:** Accepted (extended for multi-tenancy) | **Author:** @solution-architect

> **Amendment (2026-06-24) — multi-tenancy:** Two additions since this ADR was
> written (see [ADR-004](adr-004-postgresql-schema-per-school.md) and
> [ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md)):
> - A **5th role, `super_admin`**, sits above `admin`. Its token uses identity
>   `"sa:<id>"`, claim `role: super_admin`, and **no `school_slug`**; it is
>   blocklisted in the `public.super_admin_revoked_tokens` table.
> - School-user tokens now carry a **`school_slug`** claim. The tenant
>   middleware reads it on every request to select the school's PostgreSQL
>   schema. `revoked_tokens` lives inside each school schema.
> Full hierarchy: `super_admin > admin > teacher > student > parent`.

## Context
We need a Role-Based Access Control system that:
1. Works with stateless JWT (no DB lookup per request for role)
2. Supports 4 roles: Admin, Teacher, Student, Parent
3. Allows the Parent Portal to know which `parent_id` to use without an extra query
4. Remains secure against privilege escalation

## Decision

### JWT Payload Structure
```json
{
  "sub": 42,
  "role": "parent",
  "user_id": 42,
  "parent_id": 7,
  "iat": 1700000000,
  "exp": 1700000900,
  "jti": "uuid-for-revocation"
}
```

`parent_id` is included only when `role=parent`. This eliminates a DB lookup on every parent portal request.

### Role Hierarchy
```
Admin   → can access ALL endpoints
Teacher → can access teacher + shared endpoints
Student → can only access own data
Parent  → can only access parent portal + own profile
```

### RBAC Enforcement (Two layers)
1. **Route layer:** `@roles_required('admin', 'teacher')` decorator checks JWT role claim — fast, no DB hit
2. **Service layer:** Resource-level checks (e.g., parent can only see own children via `_verify_child_access()`) — catches IDOR attacks that bypass route-level guards

## Consequences
- JWT tokens carry role — role changes (e.g., student promoted to teacher) require re-login to take effect
- `parent_id` in token means parent profile must exist before token is issued
- Revocation table (`revoked_tokens`) handles logout — adds one DB lookup per request (acceptable trade-off)
