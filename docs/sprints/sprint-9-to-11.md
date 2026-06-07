# Sprints 9–11 — Communication, Reports & Hardening
**Scrum Master:** @scrum-master

---

# Sprint 9 — Communication & Library
**Sprint Goal:** Enable school-wide communication via targeted announcements and manage the library catalog with issue/return tracking.
**Velocity Target:** 26 pts | **Epic:** EPIC-10
**Dependencies:** Sprint 8 complete (parent portal notifications working — announcements feed into it)

## Sprint Board

| Story | Title | Points | Assignee |
|-------|-------|--------|----------|
| SMS-051 | Create & Publish Announcements | 5 | @backend-engineer + @frontend-engineer |
| SMS-052 | Targeted Notices (by Class/Role) | 5 | @backend-engineer |
| SMS-053 | Book Catalog Management | 5 | @backend-engineer + @frontend-engineer |
| SMS-054 | Book Issue & Return | 8 | @backend-engineer + @frontend-engineer |
| SMS-055 | Overdue Fines Calculation | 3 | @backend-engineer |

---

### SMS-051: Create & Publish Announcements — Tech Spec

**API:**
```
POST /api/v1/announcements
Role: admin
Body: {
  "title": "Parent-Teacher Meeting",
  "content": "PTM scheduled for June 15...",
  "target_roles": ["parent", "student"],    # or null for school-wide
  "target_class_ids": [3, 4],               # null = all classes
  "publish_at": "2026-06-07T08:00:00",      # scheduled publish
  "expires_at": "2026-06-20T23:59:59"
}
```

**DB:** `announcements` table:
```
id, title, content, target_roles(JSON), target_class_ids(JSON),
status['draft','published','archived'], published_at, expires_at,
created_by, created_at
```

**Notification trigger:** On publish → `NotificationService.create()` for all matching users.

**Tasks:**
| Task | Est. |
|------|------|
| Create `announcements` model + migration | 1h |
| Implement announcement CRUD with role/class targeting | 2h |
| Implement notification dispatch on publish | 1.5h |
| Build announcement editor (rich text `p-editor`) | 2h |
| Build announcement list with publish/unpublish actions | 1.5h |
| Test: school-wide, targeted, scheduled publish, notification | 1.5h |

---

### SMS-054: Book Issue & Return — Tech Spec

**API:**
```
POST /api/v1/library/issue
Body: { "book_id": 10, "student_id": 5, "due_date": "2026-06-20" }

PUT /api/v1/library/issue/:id/return
Body: { "returned_date": "2026-06-18" }
Response: { "data": { "fine_amount": 0 } }
```

**DB:**
- `library_books`: `(id, isbn, title, author, publisher, category, total_copies, available_copies)`
- `book_issues`: `(id, book_id, student_id, issued_date, due_date, returned_date, fine_amount, status)`

**Fine Calculation:** ₹5 per day overdue (configurable). On return:
```python
if returned_date > due_date:
    fine = (returned_date - due_date).days * FINE_PER_DAY
```

**Tasks:**
| Task | Est. |
|------|------|
| Create `library_books` + `book_issues` models + migration | 1.5h |
| Implement issue endpoint (check available_copies > 0) | 1.5h |
| Implement return endpoint with fine calculation | 1.5h |
| Build book catalog with search | 2h |
| Build issue/return form + active issues list | 2h |
| Test: issue, return on time, return late (fine), no copies available | 1.5h |

---

# Sprint 10 — Reports & Analytics
**Sprint Goal:** Give school leadership actionable insights through KPI dashboards and exportable reports.
**Velocity Target:** 28 pts | **Epic:** EPIC-11
**Dependencies:** Sprints 4–9 (data from all modules needed for analytics)

## Sprint Board

| Story | Title | Points | Assignee |
|-------|-------|--------|----------|
| SMS-056 | Admin KPI Dashboard | 8 | @backend-engineer + @frontend-engineer |
| SMS-057 | Attendance Analytics Report | 5 | @backend-engineer + @frontend-engineer |
| SMS-058 | Academic Performance Report | 5 | @backend-engineer + @frontend-engineer |
| SMS-059 | Fee Collection Report | 5 | @backend-engineer + @frontend-engineer |
| SMS-060 | Export Reports to PDF/Excel | 5 | @backend-engineer |

---

### SMS-056: Admin KPI Dashboard — Tech Spec

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

**Frontend:** PrimeNG dashboard layout with:
- KPI cards (4 across top): Total Students, Today's Attendance %, Monthly Fee Collection, Pending Actions
- Attendance trend chart (last 30 days, `p-chart` type=line)
- Fee collection pie chart (collected vs pending, `p-chart` type=doughnut)
- Alerts panel: low attendance students, overdue fees

**Tasks:**
| Task | Est. |
|------|------|
| Implement dashboard aggregation service | 3h |
| Implement `GET /api/v1/dashboard/admin` | 1h |
| Build KPI cards row | 1.5h |
| Build attendance trend line chart | 1.5h |
| Build fee collection doughnut chart | 1h |
| Build alerts/actions panel | 1.5h |
| Test: data accuracy, empty state, performance (< 2s response) | 1.5h |

---

### SMS-060: Export Reports to PDF/Excel — Tech Spec

**API:**
```
GET /api/v1/reports/attendance/export?format=pdf&section_id=5&from_date=...
GET /api/v1/reports/grades/export?format=excel&exam_id=3
GET /api/v1/reports/fees/export?format=pdf&as_of_date=...
```

**Libraries:**
- PDF: `WeasyPrint` (HTML → PDF)
- Excel: `openpyxl`

**Tasks:**
| Task | Est. |
|------|------|
| Implement export endpoints for attendance, grades, fees | 3h |
| Create HTML templates for PDF reports | 2h |
| Implement Excel generation with openpyxl | 2h |
| Add export buttons to each report page | 1h |
| Test: PDF content, Excel format, large dataset | 1.5h |

---

# Sprint 11 — Transport & Hardening (Release Sprint)
**Sprint Goal:** Add transport management, fix all outstanding bugs, complete security audit, optimize performance, and deliver production-ready SMS.
**Velocity Target:** 21 pts | **Epic:** EPIC-12
**Dependencies:** All previous sprints

## Sprint Board

| Story | Title | Points | Assignee |
|-------|-------|--------|----------|
| SMS-061 | Route & Vehicle Management | 5 | @backend-engineer + @frontend-engineer |
| SMS-062 | Student Transport Assignment | 5 | @backend-engineer |
| SMS-063 | Security Audit & Hardening | 5 | @security-engineer |
| SMS-064 | Performance Optimization & UAT | 6 | @devops-engineer + @qa-engineer |

---

### SMS-061: Route & Vehicle Management — Tech Spec

**API:**
```
POST /api/v1/transport/routes
Body: { "name": "Route A", "description": "North Zone", "stops": ["Stop 1", "Stop 2"] }

POST /api/v1/transport/vehicles
Body: { "registration_no": "MH01AB1234", "capacity": 40, "driver_name": "...", "route_id": 1 }
```

**DB:**
- `transport_routes`: `(id, name, description, stops_json, is_active)`
- `transport_vehicles`: `(id, registration_no, capacity, driver_name, driver_phone, route_id, is_active)`
- `student_transport`: `(id, student_id, route_id, pickup_stop, drop_stop, academic_year_id, is_active)`

---

### SMS-063: Security Audit & Hardening — Tech Spec

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

### SMS-064: Performance Optimization & UAT

**Performance Targets:**
- API response time: < 200ms for 95th percentile on student list (500+ students)
- Dashboard load: < 2s
- Report card PDF: < 5s

**Optimizations:**
- Add missing DB indexes on frequently queried columns
- Implement query result caching for dashboard stats (Redis or simple dict cache)
- Enable Flask response compression (Flask-Compress)
- Angular: verify lazy loading is working, check bundle size < 2MB

**UAT Scenarios:**
| Role | Scenario | Expected |
|------|----------|----------|
| Admin | Enroll student, assign to section, generate report card | All data flows correctly |
| Teacher | Mark attendance, enter marks, view timetable | Role restrictions work |
| Parent | View child dashboard, submit leave, message teacher | Data isolation confirmed |
| Student | View own attendance and grades | Cannot see others |
