# Sprint 3 — Teacher Management & Class Structure
**Sprint Goal:** Manage the full teacher roster and build the academic structure (classes, sections, subjects, timetables) that all other modules depend on.
**Velocity Target:** 50 pts | **Epics:** EPIC-03, EPIC-04
**Dependencies:** Sprint 2 complete

---

## Sprint Board

| Story | Title | Points | Epic | Assignee |
|-------|-------|--------|------|----------|
| SMS-014 | Teacher Registration & Profile | 8 | EPIC-03 | @backend-engineer + @frontend-engineer |
| SMS-015 | Subject Assignment to Teacher | 5 | EPIC-03 | @backend-engineer |
| SMS-016 | Teacher List & Search | 3 | EPIC-03 | @frontend-engineer |
| SMS-017 | Teacher Schedule View | 5 | EPIC-03 | @frontend-engineer |
| SMS-018 | Teacher Document Upload | 5 | EPIC-03 | @backend-engineer |
| SMS-019 | Class & Subject Catalog | 5 | EPIC-04 | @backend-engineer + @frontend-engineer |
| SMS-020 | Section Management per Class | 5 | EPIC-04 | @backend-engineer + @frontend-engineer |
| SMS-021 | Enroll Students into Sections | 5 | EPIC-04 | @backend-engineer |
| SMS-022 | Timetable Creation | 8 | EPIC-04 | @backend-engineer + @frontend-engineer |
| SMS-023 | Academic Year Management | 3 | EPIC-04 | @backend-engineer |

---

## Tech Specifications Summary

### SMS-014: Teacher Registration & Profile

**API:**
```
POST   /api/v1/teachers         # admin only
GET    /api/v1/teachers/:id
PUT    /api/v1/teachers/:id
DELETE /api/v1/teachers/:id     # soft-delete
```

**DB:** `teachers` table:
```
id, user_id, employee_id(unique), first_name, last_name, date_of_birth,
gender, qualification, specialization, joining_date, phone, address,
is_class_teacher, class_teacher_section_id, is_active, created_at
```

**Tasks:**
| Task | Layer | Est. |
|------|-------|------|
| Create `teachers` model + migration | DB | 1.5h |
| Implement teacher CRUD service | BE | 2h |
| Implement teacher routes (blueprint) | BE | 1h |
| Build teacher registration form | FE | 2h |
| Build teacher detail view (tabs: Profile / Subjects / Schedule) | FE | 2h |
| Test: CRUD, duplicate employee_id, 403 | QA | 1.5h |

---

### SMS-019: Class & Subject Catalog

**API:**
```
GET/POST/PUT/DELETE /api/v1/classes
GET/POST/PUT/DELETE /api/v1/subjects
```

**DB:**
- `classes`: `(id, name, grade_level, description, academic_year_id)`
- `subjects`: `(id, name, code, description, max_marks, pass_marks)`
- `academic_years`: `(id, name, start_date, end_date, is_current)`

**Tasks:**
| Task | Layer | Est. |
|------|-------|------|
| Create `classes`, `subjects`, `academic_years` models + migrations | DB | 2h |
| Implement CRUD routes for each entity | BE | 2h |
| Build class/subject management pages in admin panel | FE | 2h |
| Test: CRUD, validation, dependency (can't delete class with students) | QA | 1h |

---

### SMS-022: Timetable Creation

**API:**
```
GET  /api/v1/timetables?section_id=5
POST /api/v1/timetables        # create period slot
PUT  /api/v1/timetables/:id
DELETE /api/v1/timetables/:id
```

**DB:** `timetables`: `(id, section_id, subject_id, teacher_id, day_of_week, period_no, start_time, end_time)`

**Constraint check:** No teacher double-booked in same day/period slot.

**Frontend:** Weekly grid layout — rows=periods, columns=Mon–Sat. Admin drags or selects subject+teacher per cell.

**Tasks:**
| Task | Layer | Est. |
|------|-------|------|
| Create `timetables` model + migration | DB | 1h |
| Implement timetable CRUD with conflict detection | BE | 2.5h |
| Build weekly timetable grid UI | FE | 3h |
| Test: create slot, conflict detection, teacher schedule view | QA | 1.5h |
