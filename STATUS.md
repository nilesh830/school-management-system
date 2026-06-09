# SMS Project — Work Status

> Update this file at the end of every work session. It is the single source of truth for "where we left off."

---

## Current Sprint: Sprint 2 — Student Management

**Last updated:** 2026-06-09  
**Branch:** `develop`

> **ERP PIVOT:** Project is now a multi-school ERP platform. Sprint 2.5 (Multi-Tenancy Foundation) must be completed before Sprint 3. See `docs/sprints/sprint-2.5-erp-foundation.md`.

---

## Sprint 1 — Auth & User Management ✅ COMPLETE

All stories SMS-001 → SMS-006 done. 28 pytest tests pass.  
Backend + Frontend fully committed on `develop`.

**Key decisions recorded in memory:** JWT string identity, venv at `backend/venv`, seed credentials, blueprint routes use `''` not `'/'`.

---

## Sprint 2 — Student Management

### Legend
| Symbol | Meaning |
|--------|---------|
| ✅ | Done & verified |
| ⚠️ | Code written, not yet verified/tested |
| ❌ | Not started |

---

### SMS-007 — Student Enrollment

| Task | Layer | Status | Notes |
|------|-------|--------|-------|
| T-007-01 `photo_url` migration | DB | ✅ | Applied to `sms.db` |
| T-007-02 `StudentService.create()` | BE | ✅ | Duplicate 409 handled |
| T-007-03 `POST /api/v1/students` | BE | ✅ | Marshmallow schema in `backend/app/schemas/student_schema.py` |
| T-007-04 3-step stepper form | FE | ✅ | `frontend/.../students/student-new/` — lazy chunk verified in build |
| T-007-05 Client-side validators | FE | ✅ | Built into student-new component |
| T-007-06 Tests | QA | ⚠️ | `backend/tests/test_students.py` written; blocked by Python 3.14 + SQLAlchemy subprocess hang |

---

### SMS-008 — Student List (Search & Filter)

| Task | Layer | Status | Notes |
|------|-------|--------|-------|
| T-008-01/02 `get_all()` with search + section filter | BE | ✅ | `ilike` search on name + admission_no; class_id deferred to Sprint 3 |
| T-008-03/04 List component + search + filters | FE | ✅ | `frontend/.../students/student-list/` — lazy chunk in build |
| T-008-05 Empty state | FE | ⚠️ | In component, not visually verified |
| T-008-06 Tests | QA | ⚠️ | Covered in `test_students.py`, not run |

---

### SMS-009 — Student Profile View & Edit

| Task | Layer | Status | Notes |
|------|-------|--------|-------|
| T-009-01 `GET /api/v1/students/:id` | BE | ✅ | Role-gated: student can only view own |
| T-009-02 `PUT /api/v1/students/:id` | BE | ✅ | Admin full edit; student: phone+address only |
| T-009-03 Student detail page (`p-tabView`) | FE | ✅ | `frontend/.../students/student-detail/` — lazy chunk in build (267 KB) |
| T-009-04 Inline edit form | FE | ✅ | Toggle edit mode in Tab 1, Save/Cancel in header |
| T-009-05 Tests | QA | ⚠️ | In `test_students.py`, not run |

---

### SMS-010 — Parent Linking

| Task | Layer | Status | Notes |
|------|-------|--------|-------|
| T-010-01 `POST /api/v1/students/:id/parents` | BE | ✅ | Duplicate link → 409 |
| T-010-02 `DELETE /api/v1/students/:id/parents/:pid` | BE | ✅ | |
| T-010-03 JWT enrichment with `parent_id` | BE | ⚠️ | Check if login route adds `parent_id` to JWT claims |
| T-010-04 Parent linking UI (Tab 4 of detail page) | FE | ✅ | Tab 4 in student-detail: list + link/unlink with confirm |
| T-010-05 Tests | QA | ⚠️ | In `test_students.py`, not run |

---

### SMS-011 — Student Transfer Between Sections

| Task | Layer | Status | Notes |
|------|-------|--------|-------|
| T-011-01 `student_sections` model | DB | ✅ | `backend/app/models/student_section.py` |
| T-011-02 `StudentService.transfer()` | BE | ✅ | Atomic section swap with academic year calc |
| T-011-03 `POST /api/v1/students/:id/transfer` | BE | ✅ | |
| T-011-04 Transfer dialog in student detail | FE | ✅ | Transfer p-dialog in student-detail header |
| T-011-05 Tests | QA | ⚠️ | In `test_students.py`, not run |

---

### SMS-012 — Student Document Upload

| Task | Layer | Status | Notes |
|------|-------|--------|-------|
| T-012-01 `student_documents` model | DB | ✅ | `backend/app/models/student_document.py` |
| T-012-02 File upload endpoint | BE | ✅ | PDF/JPG/PNG, 5 MB limit, stored in `backend/uploads/students/<id>/` |
| T-012-03 List + delete endpoints | BE | ✅ | |
| T-012-04 Document upload tab (`p-fileUpload`) | FE | ✅ | Tab 3 in student-detail: list + p-fileUpload + delete |
| T-012-05 Tests | QA | ⚠️ | In `test_students.py`, not run |

---

### SMS-013 — Student Deactivation / Alumni

| Task | Layer | Status | Notes |
|------|-------|--------|-------|
| T-013-01 `status` + `leaving_date` migration | DB | ✅ | Enum: active/alumni/transferred/expelled |
| T-013-02 `PATCH /api/v1/students/:id/status` | BE | ✅ | |
| T-013-03 Deactivation dialog in UI | FE | ✅ | Status change dialog in Tab 2 + Deactivate quick action in header |
| T-013-04 Tests | QA | ⚠️ | In `test_students.py`, not run |

---

## What Needs Doing Next (Ordered)

1. **[BE] Verify T-010-03** — confirm parent `login` enriches JWT with `parent_id`.

3. **[QA] Run test suite** — resolve Python 3.14/SQLAlchemy subprocess issue or run manually via `.\venv\Scripts\pytest tests/ -v`.

4. **[ALL] End-to-end smoke test** — start Flask + `npx ng serve`, walk through enrollment → list → profile → deactivate.

5. **[GIT] Commit Sprint 2** — once smoke test passes, commit all unstaged/untracked files on `develop`.

---

## Pending Files to Commit (git status snapshot 2026-06-09)

```
M  backend/app/models/__init__.py
M  backend/app/models/student.py
M  backend/app/routes/students.py
M  backend/app/services/student_service.py
M  frontend/src/app/modules/admin/admin.routes.ts
?? backend/app/models/student_document.py
?? backend/app/models/student_section.py
?? backend/app/schemas/
?? backend/migrations/versions/6c69af22f07a_sprint2_...
?? backend/tests/test_students.py
?? frontend/src/app/core/services/student.service.ts
?? frontend/src/app/modules/admin/students/
```

---

## Known Issues / Blockers

| Issue | Impact | Owner |
|-------|--------|-------|
| Python 3.14 + SQLAlchemy subprocess hang | Can't run `pytest` via subprocess; manual run may work | @devops-engineer — consider Python 3.12 venv |
| `sections` table not yet created | `student_sections.section_id` FK deferred; section filter in student list is wired but unused until Sprint 3 | @database-engineer in Sprint 3 |
| `UPLOAD_FOLDER` config must exist | File upload will 500 if `backend/uploads/` dir missing | Ensure `config.py` sets `UPLOAD_FOLDER` |
