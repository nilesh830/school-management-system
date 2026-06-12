# Sprints 9–11 — Communication, Reports & Hardening
**Scrum Master:** @scrum-master

> **How to invoke agents:**
> - Database work → `@database-engineer` (models, migrations, schema)
> - Backend work → `@backend-engineer` (routes, services, business logic, tests)
> - Frontend work → `@frontend-engineer` (Angular components, PrimeNG UI, HTTP services)
> - Security work → `@security-engineer` (OWASP, pen-test, audit)
> - DevOps work → `@devops-engineer` (Docker, CI/CD, performance)
> - QA work → `@qa-engineer` (test plans, E2E, coverage)

---

# Sprint 9 — Communication & Library
**Sprint Goal:** Enable school-wide communication via targeted announcements and manage the library catalog with issue/return tracking.
**Velocity Target:** 26 pts | **Epic:** EPIC-10
**Dependencies:** Sprint 8 complete (parent portal notifications working — announcements feed into it)

## Sprint Board

| Story | Title | Points | Agents |
|-------|-------|--------|--------|
| SMS-051 | Create & Publish Announcements | 5 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` |
| SMS-052 | Targeted Notices (by Class/Role) | 5 | `@backend-engineer` |
| SMS-053 | Book Catalog Management | 5 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` |
| SMS-054 | Book Issue & Return | 8 | `@backend-engineer` → `@frontend-engineer` |
| SMS-055 | Overdue Fines Calculation | 3 | `@backend-engineer` |

---

### SMS-051: Create & Publish Announcements

**DB Schema:**
```
announcements: (id, title, content TEXT, target_roles JSON, target_class_ids JSON,
                status ENUM['draft','published','archived'], published_at DATETIME,
                expires_at DATETIME, created_by FK→users.id, created_at)
```

**API:**
```
POST /api/v1/announcements
Role: admin
Body: {
  "title": "Parent-Teacher Meeting",
  "content": "PTM scheduled for June 15...",
  "target_roles": ["parent", "student"],    # null = school-wide
  "target_class_ids": [3, 4],              # null = all classes
  "publish_at": "2026-06-07T08:00:00",
  "expires_at": "2026-06-20T23:59:59"
}

GET  /api/v1/announcements          → list (admin: all; others: published only)
GET  /api/v1/announcements/:id      → single
PUT  /api/v1/announcements/:id      → update (admin)
POST /api/v1/announcements/:id/publish  → publish draft
```

**Notification trigger:** On publish → `NotificationService.create()` for all matching users.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-051-01 | Create `Announcement` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-051-02 | Implement `AnnouncementService` CRUD + `publish()` method | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-051-03 | Implement announcement routes blueprint | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-051-04 | Dispatch notification to matching users on publish | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-051-05 | Build announcement editor (rich text `p-editor`) + list with publish actions | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 3.5h |
| T-051-06 | Tests: create, publish, school-wide dispatch, class-targeted dispatch | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |

---

### SMS-052: Targeted Notices (by Class/Role)

**Logic:** `AnnouncementService.get_for_user(user_id, role, class_ids)` filters by `target_roles` and `target_class_ids` columns (JSON contains check).

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-052-01 | Implement `AnnouncementService.get_for_user()` with role + class filtering | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-052-02 | `GET /api/v1/announcements?role_view=true` — returns only relevant notices for current user | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-052-03 | Tests: parent sees only parent-targeted, class-specific filtering, archived exclusion | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-052-04 | Target selector in announcement form (role checkboxes + class multi-select) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |

---

### SMS-053: Book Catalog Management

**DB Schema:**
```
library_books: (id, isbn VARCHAR(20) UNIQUE, title, author, publisher, category,
                total_copies INT, available_copies INT, is_active)
```

**API:**
```
POST   /api/v1/library/books          → add book (admin)
GET    /api/v1/library/books          → list + search (admin, teacher)
PUT    /api/v1/library/books/:id      → update
DELETE /api/v1/library/books/:id      → soft delete (blocked if active issues)
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-053-01 | Create `LibraryBook` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-053-02 | Implement `LibraryService` book CRUD | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-053-03 | Implement library routes blueprint | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-053-04 | Build book catalog with search + add/edit dialog | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-053-05 | Tests: create book, list + search, update, delete blocked with active issues | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-054: Book Issue & Return

**DB Schema:**
```
book_issues: (id, book_id FK, student_id FK, issued_date DATE, due_date DATE,
              returned_date DATE NULLABLE, fine_amount NUMERIC(8,2) default 0,
              status ENUM['issued','returned','overdue'], issued_by FK→users.id)
```

**API:**
```
POST /api/v1/library/issue
Body: { "book_id": 10, "student_id": 5, "due_date": "2026-06-20" }
Validates: available_copies > 0

PUT /api/v1/library/issue/:id/return
Body: { "returned_date": "2026-06-18" }
Response: { "data": { "fine_amount": 0 } }
```

**Fine Calculation:** ₹5 per day overdue (configurable). `available_copies` decremented on issue, incremented on return.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-054-01 | Create `BookIssue` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-054-02 | Implement `LibraryService.issue_book()` with available_copies check | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-054-03 | Implement `LibraryService.return_book()` with fine calculation | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-054-04 | Implement issue + return endpoints | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-054-05 | Build issue/return form + active issues list per student | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-054-06 | Build book catalog view with available copies badge | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-054-07 | Tests: issue, return on time, return late (fine), no copies available 409 | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |

---

### SMS-055: Overdue Fines Calculation

**Logic:** Daily job (or triggered on return) identifies overdue issues and updates `status='overdue'` + computes `fine_amount`.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-055-01 | Implement `LibraryService.mark_overdue()` — scan for passed due_dates | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-055-02 | Expose `GET /api/v1/library/overdue` — all overdue issues | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-055-03 | Show overdue fine in student library view | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 0.5h |
| T-055-04 | Tests: fine calculation per day, mark overdue logic | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

# Sprint 10 — Reports & Analytics
**Sprint Goal:** Give school leadership actionable insights through KPI dashboards and exportable reports.
**Velocity Target:** 28 pts | **Epic:** EPIC-11
**Dependencies:** Sprints 4–9 (data from all modules needed for analytics)

## Sprint Board

| Story | Title | Points | Agents |
|-------|-------|--------|--------|
| SMS-056 | Admin KPI Dashboard | 8 | `@backend-engineer` → `@frontend-engineer` |
| SMS-057 | Attendance Analytics Report | 5 | `@backend-engineer` → `@frontend-engineer` |
| SMS-058 | Academic Performance Report | 5 | `@backend-engineer` → `@frontend-engineer` |
| SMS-059 | Fee Collection Report | 5 | `@backend-engineer` → `@frontend-engineer` |
| SMS-060 | Export Reports to PDF/Excel | 5 | `@backend-engineer` |

---

### SMS-056: Admin KPI Dashboard

**API:**
```
GET /api/v1/dashboard/admin
Response: {
  "data": {
    "total_students": 1250,
    "total_teachers": 48,
    "attendance_today": { "present": 1100, "absent": 150, "percentage": 88.0 },
    "fee_collection_this_month": { "collected": 850000, "pending": 120000 },
    "pending_leave_applications": 12,
    "recent_announcements": [...],
    "low_attendance_students": [...],    # attendance < 75%
    "fee_defaulters_count": 23
  }
}
```

**Frontend:** PrimeNG dashboard layout:
- 4 KPI cards across top: Total Students, Today's Attendance %, Monthly Fee Collection, Pending Actions
- Attendance trend chart (last 30 days, `p-chart` type=line)
- Fee collection doughnut chart (collected vs pending)
- Alerts panel: low attendance students, overdue fees

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-056-01 | Implement `DashboardService.get_admin_kpis()` aggregating all modules | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 3h |
| T-056-02 | Implement `GET /api/v1/dashboard/admin` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-056-03 | Build 4 KPI cards row with PrimeFlex grid | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1.5h |
| T-056-04 | Build attendance trend line chart (last 30 days) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1.5h |
| T-056-05 | Build fee collection doughnut chart | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-056-06 | Build alerts/pending actions panel | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1.5h |
| T-056-07 | Tests: data accuracy, empty state, response time < 2s | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |

---

### SMS-057: Attendance Analytics Report

**API:**
```
GET /api/v1/reports/attendance?section_id=5&from_date=2026-06-01&to_date=2026-06-30
Response: per-student attendance counts + class average
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-057-01 | Implement attendance analytics query with groupBy student | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-057-02 | Implement `GET /api/v1/reports/attendance` with date range + section filter | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-057-03 | Build attendance report page (table + bar chart per student) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-057-04 | Tests: date range filter, section filter, class average | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-058: Academic Performance Report

**API:**
```
GET /api/v1/reports/grades?exam_id=3&section_id=5
Response: all students' results for an exam with subject breakdown
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-058-01 | Implement grade report aggregation per exam + section | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-058-02 | Implement `GET /api/v1/reports/grades` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-058-03 | Build class result summary table with grade distribution chart | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-058-04 | Tests: multi-section, empty exam, grade distribution | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-059: Fee Collection Report

**API:**
```
GET /api/v1/reports/fees?class_id=3&academic_year_id=1
Response: collected vs pending per fee type, defaulters list
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-059-01 | Implement fee collection aggregation query | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-059-02 | Implement `GET /api/v1/reports/fees` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-059-03 | Build fee report page (collection summary + defaulters table) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-059-04 | Tests: class filter, academic year filter, collection totals | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-060: Export Reports to PDF/Excel

**API:**
```
GET /api/v1/reports/attendance/export?format=pdf&section_id=5&from_date=...
GET /api/v1/reports/grades/export?format=excel&exam_id=3
GET /api/v1/reports/fees/export?format=pdf&as_of_date=...
```

**Libraries:** PDF → `WeasyPrint` | Excel → `openpyxl`

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-060-01 | Add `openpyxl` to `requirements.txt`, implement Excel generator helper | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-060-02 | Implement export endpoints for attendance, grades, fees (PDF + Excel) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 3h |
| T-060-03 | Create HTML PDF templates for each report type | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-060-04 | Add export buttons (PDF / Excel) to each report page | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-060-05 | Tests: PDF content, Excel format, large dataset (500+ rows) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |

---

# Sprint 11 — Transport & Hardening (Release Sprint)
**Sprint Goal:** Add transport management, fix all outstanding bugs, complete security audit, optimize performance, and deliver production-ready SMS.
**Velocity Target:** 21 pts | **Epic:** EPIC-12
**Dependencies:** All previous sprints

## Sprint Board

| Story | Title | Points | Agents |
|-------|-------|--------|--------|
| SMS-061 | Route & Vehicle Management | 5 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` |
| SMS-062 | Student Transport Assignment | 5 | `@backend-engineer` → `@frontend-engineer` |
| SMS-063 | Security Audit & Hardening | 5 | `@security-engineer` |
| SMS-064 | Performance Optimization & UAT | 6 | `@devops-engineer` + `@qa-engineer` |

---

### SMS-061: Route & Vehicle Management

**DB Schema:**
```
transport_routes:   (id, name, description, stops_json JSON, is_active)
transport_vehicles: (id, registration_no UNIQUE, capacity INT,
                     driver_name, driver_phone, route_id FK, is_active)
```

**API:**
```
POST /api/v1/transport/routes
Body: { "name": "Route A", "description": "North Zone", "stops": ["Stop 1", "Stop 2"] }

POST /api/v1/transport/vehicles
Body: { "registration_no": "MH01AB1234", "capacity": 40, "driver_name": "...", "route_id": 1 }

GET /api/v1/transport/routes   → list
GET /api/v1/transport/vehicles → list (filter by route_id)
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-061-01 | Create `TransportRoute` + `TransportVehicle` models + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-061-02 | Implement `TransportService` CRUD for routes + vehicles | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-061-03 | Implement transport routes blueprint | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-061-04 | Build route list + vehicle list in admin panel | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-061-05 | Tests: create route, add vehicle to route, list by route | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-062: Student Transport Assignment

**DB Schema:**
```
student_transport: (id, student_id FK, route_id FK, pickup_stop VARCHAR(100),
                    drop_stop VARCHAR(100), academic_year_id FK, is_active)
UniqueConstraint(student_id, academic_year_id)
```

**API:**
```
POST /api/v1/transport/assignments
Body: { "student_id": 5, "route_id": 1, "pickup_stop": "Stop 2", "drop_stop": "Stop 5", "academic_year_id": 1 }

GET /api/v1/transport/assignments?route_id=1     → all students on a route
GET /api/v1/students/:id/transport               → student's current transport
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-062-01 | Create `StudentTransport` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 0.5h |
| T-062-02 | Implement `TransportService.assign_student()` + unassign | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-062-03 | Implement assignment endpoints | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-062-04 | Build student transport assignment form in admin student detail | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-062-05 | Tests: assign, reassign (closes old), unassign, list by route | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-063: Security Audit & Hardening

**Audit Checklist (run by @security-engineer):**
- [ ] OWASP Top 10 review of all endpoints
- [ ] Verify all routes have `@jwt_required()` or `@roles_required()`
- [ ] Run `pip audit` — fix all critical CVEs
- [ ] Run `npm audit` — fix critical CVEs
- [ ] Check all `to_dict()` methods exclude sensitive fields
- [ ] Verify CORS settings for production origin
- [ ] Verify rate limiting on auth endpoints
- [ ] Run Trivy scan on Docker images
- [ ] Penetration test: SQL injection, XSS, CSRF, IDOR
- [ ] Review Parent Portal data isolation (no cross-parent data leakage)

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-063-01 | OWASP Top 10 audit on all endpoints — create findings report | [`@security-engineer`](.claude/agents/security-engineer.md) | 3h |
| T-063-02 | Run `pip audit` + `npm audit` — fix critical CVEs | [`@security-engineer`](.claude/agents/security-engineer.md) | 1h |
| T-063-03 | Penetration test: SQL injection, IDOR, auth bypass | [`@security-engineer`](.claude/agents/security-engineer.md) | 2h |
| T-063-04 | Verify rate limiting on `/api/v1/auth/login` | [`@security-engineer`](.claude/agents/security-engineer.md) | 0.5h |
| T-063-05 | Fix all findings — harden endpoints + update CORS for production | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |

---

### SMS-064: Performance Optimization & UAT

**Performance Targets:**
- API response time: < 200ms (95th percentile) on student list (500+ students)
- Dashboard load: < 2s
- Report card PDF: < 5s

**Optimizations:**
- Add missing DB indexes on frequently queried columns
- Implement caching for dashboard stats (Redis or simple dict cache)
- Enable Flask response compression (`Flask-Compress`)
- Angular: verify lazy loading, check bundle size < 2MB

**UAT Scenarios:**
| Role | Scenario | Expected |
|------|----------|----------|
| Admin | Enroll student → assign to section → generate report card | All data flows correctly |
| Teacher | Mark attendance → enter marks → view timetable | Role restrictions work |
| Parent | View child dashboard → submit leave → message teacher | Data isolation confirmed |
| Student | View own attendance and grades | Cannot see others' data |

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-064-01 | Add missing DB indexes on high-frequency columns (student_id, section_id, date) | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-064-02 | Implement dashboard stats caching (5-min TTL) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-064-03 | Add `Flask-Compress` for gzip response compression | [`@devops-engineer`](.claude/agents/devops-engineer.md) | 0.5h |
| T-064-04 | Load test: 500 students list, dashboard, report card PDF | [`@qa-engineer`](.claude/agents/qa-engineer.md) | 2h |
| T-064-05 | Run UAT across all 4 roles — document pass/fail | [`@qa-engineer`](.claude/agents/qa-engineer.md) | 3h |
| T-064-06 | Fix any UAT failures | [`@backend-engineer`](.claude/agents/backend-engineer.md) + [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-064-07 | Docker production build + smoke test | [`@devops-engineer`](.claude/agents/devops-engineer.md) | 1h |
