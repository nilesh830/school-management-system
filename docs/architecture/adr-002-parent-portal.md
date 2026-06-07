# ADR-002: Parent Portal — Integrated vs Separate Application
**Date:** 2026-06-06 | **Status:** Accepted | **Author:** @solution-architect

## Context
The Parent Portal needs to serve parents with a mobile-friendly, restricted view of their children's data. We must decide whether to build it as a separate application or integrate it into the existing SMS Angular SPA.

## Options Considered

### Option A: Separate Angular Application (subdomain: parent.school.sms)
- Pros: Complete isolation, independent deployment, separate bundle
- Cons: Duplicated auth code, shared API but separate frontend codebase, maintenance overhead, 2× CI pipelines

### Option B: Role-scoped Module in existing SPA (Chosen)
- Pros: Single codebase, shared auth/guards/interceptors, shared services, one CI pipeline
- Cons: Slightly larger bundle (mitigated by lazy loading)

## Decision
**Option B** — Parent Portal as a lazy-loaded Angular module within the same SPA, at route `/parent/*`.

The `parent` JWT role claim gates access. A dedicated `parent-portal.module.ts` is lazy-loaded only when a parent logs in, so non-parent users never download its code.

The backend uses a dedicated `/api/v1/parent-portal/*` Blueprint with `@roles_required('parent')` on every route, and `_verify_child_access()` enforced at the service layer.

## Consequences
- One deployment, one CI pipeline
- Parent bundle loaded only on demand (~0 cost for admin/teacher users)
- Data isolation is enforced at API layer — Angular routing is defense-in-depth only
- If the parent portal grows very large in future, it can be extracted to a micro-frontend without API changes
