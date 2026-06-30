# SMS — Master Product Backlog
**Product Owner:** @product-owner | **Architect:** @solution-architect | **Scrum Master:** @scrum-master
**Last Updated:** 2026-06-06 | **Total Story Points:** 283 | **Total Sprints:** 11

---

## Epic Overview

| Epic ID | Module | Stories | Points | Sprint(s) |
|---------|--------|---------|--------|-----------|
| EPIC-01 | Authentication & Authorization | 6 | 32 | 1 |
| EPIC-02 | Student Management | 7 | 35 | 2 |
| EPIC-03 | Teacher Management | 5 | 25 | 3 |
| EPIC-04 | Class & Section Management | 5 | 25 | 3 |
| EPIC-05 | Attendance Management | 5 | 28 | 4 |
| EPIC-06 | Grade & Exam Management | 6 | 33 | 5 |
| EPIC-07 | Fee Management | 6 | 32 | 6 |
| EPIC-08 | Parent Portal — Core | 5 | 30 | 7 |
| EPIC-09 | Parent Portal — Communication | 5 | 28 | 8 |
| EPIC-10 | Communication & Library | 5 | 24 | 9 |
| EPIC-11 | Reports & Analytics | 5 | 25 | 10 |
| EPIC-12 | Transport & Hardening | 4 | 21 | 11 |

---

## EPIC-01: Authentication & Authorization
**Goal:** Secure JWT-based login with role-aware access for all user types.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-001 | User Login with JWT | 5 | Must | 1 |
| SMS-002 | Token Refresh & Logout | 3 | Must | 1 |
| SMS-003 | Admin User Registration | 5 | Must | 1 |
| SMS-004 | Role-Based Frontend Route Guards | 5 | Must | 1 |
| SMS-005 | Password Reset Flow | 8 | Should | 1 |
| SMS-006 | User Profile View & Edit | 6 | Should | 1 |

## EPIC-02: Student Management
**Goal:** Full lifecycle management of student records from enrollment to alumni.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-007 | Student Enrollment | 8 | Must | 2 |
| SMS-008 | Student List (Search & Filter) | 5 | Must | 2 |
| SMS-009 | Student Profile View & Edit | 5 | Must | 2 |
| SMS-010 | Parent Linking to Student | 5 | Must | 2 |
| SMS-011 | Student Transfer Between Sections | 5 | Should | 2 |
| SMS-012 | Student Document Upload | 5 | Should | 2 |
| SMS-013 | Student Deactivation / Alumni | 3 | Could | 2 |

## EPIC-03: Teacher Management
**Goal:** Manage teacher profiles, subject assignments, and scheduling.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-014 | Teacher Registration & Profile | 8 | Must | 3 |
| SMS-015 | Subject Assignment to Teacher | 5 | Must | 3 |
| SMS-016 | Teacher List & Search | 3 | Must | 3 |
| SMS-017 | Teacher Schedule View | 5 | Should | 3 |
| SMS-018 | Teacher Document Upload | 5 | Could | 3 |

## EPIC-04: Class & Section Management
**Goal:** Manage academic structure — grades, sections, subjects, timetables.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-019 | Class & Subject Catalog | 5 | Must | 3 |
| SMS-020 | Section Management per Class | 5 | Must | 3 |
| SMS-021 | Enroll Students into Sections | 5 | Must | 3 |
| SMS-022 | Timetable Creation | 8 | Should | 3 |
| SMS-023 | Academic Year Management | 3 | Should | 3 |
| SMS-065 | Optional Sections (Class-only enrollment for section-less schools) | 5 | Should | TBD |

## EPIC-05: Attendance Management
**Goal:** Daily attendance tracking with parent alerts and analytics.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-024 | Mark Daily Attendance (Teacher) | 8 | Must | 4 |
| SMS-025 | Attendance View (Student/Parent) | 5 | Must | 4 |
| SMS-026 | Attendance Report by Class & Range | 8 | Must | 4 |
| SMS-027 | Absence Notification to Parent | 5 | Should | 4 |
| SMS-028 | Attendance Statistics Dashboard | 3 | Could | 4 |

## EPIC-06: Grade & Exam Management
**Goal:** Create exams, enter marks, calculate GPA, generate report cards.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-029 | Create Exam Definitions | 5 | Must | 5 |
| SMS-030 | Subject-wise Marks Entry | 8 | Must | 5 |
| SMS-031 | Grade Calculation & GPA | 5 | Must | 5 |
| SMS-032 | Student Report Card Generation | 8 | Must | 5 |
| SMS-033 | Class Result Summary | 5 | Should | 5 |
| SMS-034 | Marks Edit & Approval Workflow | 5 | Should | 5 |

## EPIC-07: Fee Management
**Goal:** Define fee structures, generate obligations, record payments, issue receipts.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-035 | Fee Structure per Class | 5 | Must | 6 |
| SMS-036 | Generate Student Fee Records | 5 | Must | 6 |
| SMS-037 | Record Fee Payment | 8 | Must | 6 |
| SMS-038 | Fee Receipt PDF Generation | 5 | Must | 6 |
| SMS-039 | Fee Arrears & Defaulter Report | 5 | Should | 6 |
| SMS-040 | Discount & Scholarship Management | 5 | Could | 6 |
| SMS-066 | Fee Applicability — optional/opt-in fees & per-student billing | 8 | Should | In Progress |

## EPIC-08: Parent Portal — Core (Read)
**Goal:** Give parents real-time visibility into their child's school life.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-041 | Parent Dashboard (All Children Overview) | 8 | Must | 7 |
| SMS-042 | Child Attendance Monitor | 8 | Must | 7 |
| SMS-043 | Academic Performance View | 8 | Must | 7 |
| SMS-044 | Fee Status & History | 5 | Must | 7 |
| SMS-045 | School Notice Board (Parent View) | 3 | Must | 7 |

## EPIC-09: Parent Portal — Communication (Interactive)
**Goal:** Enable parents to act — apply leave, message teachers, manage profile.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-046 | Leave Application Submission | 8 | Must | 8 |
| SMS-047 | Leave Application Tracking & Review | 5 | Must | 8 |
| SMS-048 | Parent-Teacher Messaging | 8 | Should | 8 |
| SMS-049 | In-App Notifications (Parent) | 5 | Must | 8 |
| SMS-050 | Parent Profile Management | 3 | Must | 8 |

## EPIC-10: Communication & Library
**Goal:** School-wide announcements and library management.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-051 | Create & Publish Announcements | 5 | Must | 9 |
| SMS-052 | Targeted Notices (by Class/Role) | 5 | Must | 9 |
| SMS-053 | Book Catalog Management | 5 | Must | 9 |
| SMS-054 | Book Issue & Return | 8 | Must | 9 |
| SMS-055 | Overdue Fines Calculation | 3 | Should | 9 |

## EPIC-11: Reports & Analytics
**Goal:** Actionable dashboards and exportable reports for school leadership.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-056 | Admin KPI Dashboard | 8 | Must | 10 |
| SMS-057 | Attendance Analytics Report | 5 | Must | 10 |
| SMS-058 | Academic Performance Report | 5 | Must | 10 |
| SMS-059 | Fee Collection Report | 5 | Must | 10 |
| SMS-060 | Export Reports to PDF/Excel | 5 | Should | 10 |

## EPIC-12: Transport & Hardening
**Goal:** Transport management + production-readiness hardening.

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|--------|----------|--------|
| SMS-061 | Route & Vehicle Management | 5 | Should | 11 |
| SMS-062 | Student Transport Assignment | 5 | Should | 11 |
| SMS-063 | Security Audit & Hardening | 5 | Must | 11 |
| SMS-064 | Performance Optimization & UAT | 6 | Must | 11 |

---

## Backlog — Unscheduled Enhancements

### SMS-065: Optional Sections (Class-only enrollment for section-less schools)
**Epic:** EPIC-04 (Class & Section Management) | **Points:** 5 (est.) | **Priority:** Should | **Sprint:** TBD
**Raised:** 2026-06-30 — "discuss later" (deferred for design discussion)

**Problem / Business context:**
Some schools do not use sections — a class *is* the group of students (e.g. one Grade-10 group of 30, no A/B/C split). The system is currently section-centric: students can only be enrolled into a `Section`, never directly into a `Class`. In the enrollment flow the Class/Section dropdown is fed by `getSections()`, so a class with zero sections cannot be selected, blocking enrollment. This surfaced in production where classes existed but had no sections ("No sections found — create classes & sections first").

**Constraint (why it's not trivial):** `section` is the atomic operating unit — `student_sections.section_id` is NOT NULL, and attendance / exams / timetable all hang off `section_id`. A class with no section has nowhere to attach students, attendance, or marks.

**Recommended approach (Option A — "default section" pattern):** Keep section as the atomic unit (no rearchitecting). Auto-create one default section when a class is created; in single-section classes show the *class name only* in the UI (hide the word "section"). Optionally add a school-level `uses_sections` setting later (Option C) to fully hide the section concept.

**Acceptance criteria (draft):**
- Creating a class auto-provisions one default section for that class.
- One-time backfill: every existing class with 0 sections gets a default section (prod has these).
- Enrollment dropdown shows `"Class X"` when a class has only its default section; shows `"Class X — A/B"` only when 2+ named sections exist.
- Attendance / exams / timetable continue to work unchanged.
- Schools that use sections see no behavior change.

**Touch points:**
- Backend: class-create service → also create default section; backfill script.
- Frontend: dropdown label logic in `student-new.component.ts` (collapse to class name for lone default section).

**Alternatives considered:** Option B (make `section_id` nullable + add `class_id` to enrollment) — rejected as high-cost/high-risk; forces branching join logic across attendance/grades/timetable/fees permanently.

---

### SMS-066: Fee Applicability — optional/opt-in fees & per-student billing
**Epic:** EPIC-07 (Fee Management) | **Points:** 8 (est.) | **Priority:** Should | **Status:** In Progress (design)
**Raised:** 2026-06-30 — active development started with @solution-architect → @database-engineer → @backend-engineer → @frontend-engineer.

**Problem / Business context:**
Fee generation currently bills *every* active student in a class the same set of fees (`FeeService.generate_records_for_class` iterates all students of the class linked to a `FeeStructure`). In reality fees are not uniform:
- **Mandatory / class-wide fees** (tuition, admission, exam) — correctly apply to all students in the class.
- **Optional / opt-in fees** (transport, hostel, optional activities) — apply only to students who subscribed, and the amount often varies per student (e.g. transport fare by route/distance).

Today there is no way to mark a fee as optional, so opt-in fees get billed to the whole class. Transport in particular can't even be modelled: `TransportRoute` has **no fare field**, and `StudentTransport` (the natural opt-in/subscription table) is not linked to fee generation.

**Recommended approach ("Applicability" pattern — keep class-wide blanket for mandatory fees):**
1. Add `applicability` to `FeeStructure`: `mandatory` (default = current behaviour, all students in class) vs `optional` (opt-in only).
2. Optional-fee generation bills only opted-in students.
3. Transport: add `fare` (+ frequency) to `TransportRoute`; generate transport fees from active `StudentTransport` assignments using the student's route fare — not a flat class amount.
4. Per-student tweaks already partly supported: `FeeRecord.discount` / `net_amount` + `Discount` model (ties into SMS-040). Consider an explicit `amount_override` for custom per-student amounts.

**Acceptance criteria (draft):**
- A fee structure can be created as Mandatory or Optional in the admin UI.
- Generating a Mandatory fee behaves exactly as today (no regression).
- Generating an Optional fee creates records only for students who opted in.
- Transport routes carry a fare; a student assigned to a route is billed that route's fare at the configured frequency.
- Students who did not opt in are never billed an optional fee.
- Existing fee structures default to `mandatory` on migration (no behaviour change for current data).

**Constraint (multi-tenancy):** schema change must migrate across **every** tenant DB. Note the known gotcha: `db upgrade-all` fails on ALTER when `search_path` is pinned to `public` — per-schema DDL may need to be applied directly (see `project_schema_migration_gotcha`). Migration strategy is part of the architect's deliverable.

**Touch points:**
- DB: `fee_structures.applicability` column; `transport_routes.fare` (+ frequency); migration + backfill defaulting existing rows to `mandatory`.
- Backend: branch in `FeeService.generate_records_for_class` on applicability; transport-fee generation path off `StudentTransport`; Marshmallow schema updates.
- Frontend: fee-structure form gets a Mandatory/Optional selector; route form gets a fare field; generation UX communicates who will be billed.

**Alternatives considered:** Make *all* fees student-specific — rejected: removes the convenience of setting class-wide fees once and 10×'s admin effort for the common (mandatory) case.
