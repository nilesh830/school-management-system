# ADR-003: JWT Claims Strategy & RBAC Design
**Date:** 2026-06-06 | **Status:** Accepted | **Author:** @solution-architect

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
