# Sprint 2 — Student Management
**Scrum Master:** @scrum-master | **Dates:** Week 3–4
**Sprint Goal:** Full student lifecycle — enrollment, search, profile, parent linking — so the school can manage its student population end-to-end.
**Velocity Target:** 35 pts | **Epic:** EPIC-02
**Dependencies:** Sprint 1 must be complete (auth working, users seeded)

---

## Sprint Board

| Story | Title | Points | Assignee | Status |
|-------|-------|--------|----------|--------|
| SMS-007 | Student Enrollment | 8 | @backend-engineer + @frontend-engineer | To Do |
| SMS-008 | Student List (Search & Filter) | 5 | @backend-engineer + @frontend-engineer | To Do |
| SMS-009 | Student Profile View & Edit | 5 | @frontend-engineer | To Do |
| SMS-010 | Parent Linking to Student | 5 | @backend-engineer + @frontend-engineer | To Do |
| SMS-011 | Student Transfer Between Sections | 5 | @backend-engineer | To Do |
| SMS-012 | Student Document Upload | 5 | @backend-engineer + @frontend-engineer | To Do |
| SMS-013 | Student Deactivation / Alumni | 3 | @backend-engineer | To Do |

---

## Stories — Full Detail

---

### SMS-007: Student Enrollment
**Epic:** EPIC-02 | **Points:** 8 | **Priority:** Must

**User Story:**
> As a school admin,
> I want to enroll a new student with their personal details and assign an admission number,
> So that the student has an official record in the system and can be assigned to a class.

**Acceptance Criteria:**
- [ ] Given I am admin, When I POST `/api/v1/students`, Then a student record is created with a unique `admission_no`
- [ ] Given duplicate `admission_no`, When I enroll, Then I receive HTTP 409
- [ ] Given missing required fields (name, DOB, gender, admission date), Then I receive HTTP 422 with field errors
- [ ] Given enrollment succeeds, Then the student also appears in the student list immediately
- [ ] Given I submit the Angular form, Then all required fields are validated client-side before API call

**Dependencies:** SMS-003 (user creation — student user must exist to link)

---

#### Tech Specification — SMS-007

**Backend API:**
```
POST /api/v1/students
Role Required: admin
Body: {
  "admission_no": "ADM2024001",
  "first_name": "Alice",
  "last_name": "Johnson",
  "date_of_birth": "2010-05-15",
  "gender": "Female",
  "admission_date": "2024-01-15",
  "blood_group": "O+",
  "address": "123 Main St",
  "phone": "9876543210",
  "user_id": 5
}
Response 201: { "data": { "id": 1, "admission_no": "ADM2024001", ... } }
Response 409: { "message": "Admission number already exists" }
Response 422: { "errors": { "first_name": ["required"] } }
```

**Database:** `students` table (already modeled). New migration adds:
- `photo_url` column (nullable, for profile photo)

**Frontend Components:**
- `/admin/students/new` — multi-step PrimeNG `p-stepper` form:
  - Step 1: Personal Info (name, DOB, gender, blood group)
  - Step 2: Admission Info (admission_no, date, class preference)
  - Step 3: Contact (address, phone)
- `StudentService.createStudent()` — POST to API

---

#### Tasks — SMS-007

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-007-01 | Add `photo_url` column to students migration | DB | @database-engineer | 0.5h |
| T-007-02 | Implement `StudentService.create()` with duplicate check | BE | @backend-engineer | 1.5h |
| T-007-03 | Implement `POST /api/v1/students` with Marshmallow validation | BE | @backend-engineer | 1.5h |
| T-007-04 | Build student enrollment stepper form (3 steps) | FE | @frontend-engineer | 3h |
| T-007-05 | Add client-side Reactive Form validators | FE | @frontend-engineer | 1h |
| T-007-06 | Test: valid enrollment, duplicate admission_no, missing fields, 403 | QA | @qa-engineer | 2h |

---

### SMS-008: Student List (Search & Filter)
**Epic:** EPIC-02 | **Points:** 5 | **Priority:** Must

**User Story:**
> As an admin or teacher,
> I want to see a paginated, searchable list of all students,
> So that I can quickly find a student by name, admission number, or class.

**Acceptance Criteria:**
- [ ] Given I am admin or teacher, When I GET `/api/v1/students`, Then I see a paginated list (20/page default)
- [ ] Given I search by name, Then results filter in real-time (debounced)
- [ ] Given I filter by class/section, Then only students in that class appear
- [ ] Given 0 results, Then an empty state message is shown (not an empty table)
- [ ] Given role=student or role=parent, When they access this endpoint, Then HTTP 403

**Dependencies:** SMS-007

---

#### Tech Specification — SMS-008

**Backend API:**
```
GET /api/v1/students?page=1&per_page=20&search=alice&class_id=3&section_id=5
Role Required: admin, teacher
Response 200: {
  "data": {
    "students": [...],
    "meta": { "total": 150, "page": 1, "per_page": 20, "pages": 8 }
  }
}
```

**Frontend Components:**
- `/admin/students` — PrimeNG `p-table` with lazy loading
- Search input with 400ms `debounceTime` on `valueChanges`
- Class/Section filter dropdowns (populated from `/api/v1/classes`)
- Export button (triggers CSV download via backend)

---

#### Tasks — SMS-008

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-008-01 | Add `class_id`/`section_id` filter to `StudentService.get_all()` | BE | @backend-engineer | 1h |
| T-008-02 | Implement search across name + admission_no using SQLAlchemy `ilike` | BE | @backend-engineer | 0.5h |
| T-008-03 | Build student list component with lazy PrimeNG table | FE | @frontend-engineer | 2h |
| T-008-04 | Add search input with debounce + filter dropdowns | FE | @frontend-engineer | 1.5h |
| T-008-05 | Handle empty state (0 results) | FE | @frontend-engineer | 0.5h |
| T-008-06 | Test: pagination, search, filter by class, 403 for student role | QA | @qa-engineer | 1.5h |

---

### SMS-009: Student Profile View & Edit
**Epic:** EPIC-02 | **Points:** 5 | **Priority:** Must

**User Story:**
> As an admin,
> I want to view and edit a student's full profile,
> So that I can keep their records accurate and up to date.

**Acceptance Criteria:**
- [ ] Given I click a student row, Then I see their full profile page
- [ ] Given I click Edit, Then an editable form is shown with current values pre-populated
- [ ] Given I submit valid changes, Then the student record is updated
- [ ] Given I am the student viewing my own profile, Then I see my data but cannot edit admission_no or DOB
- [ ] Given role=parent, When they view a linked child's profile, Then they see a read-only view

**Dependencies:** SMS-007, SMS-008

---

#### Tech Specification — SMS-009

**Backend API:**
```
GET  /api/v1/students/:id  → full student profile
PUT  /api/v1/students/:id  → update (admin only: all fields; student: name, phone, address only)
```

**Role-scoped edit logic:**
- Admin: can edit all fields
- Student: can only edit `phone`, `address` (their own record only)
- Parent: read-only view (via Parent Portal, not this endpoint)

**Frontend:** `/admin/students/:id` — tabbed layout:
- Tab 1: Personal Info
- Tab 2: Enrollment & Academic Info
- Tab 3: Documents
- Tab 4: Parent/Guardian Info

---

#### Tasks — SMS-009

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-009-01 | Implement `GET /api/v1/students/:id` with role-based field exposure | BE | @backend-engineer | 1h |
| T-009-02 | Implement `PUT /api/v1/students/:id` with role-scoped field whitelist | BE | @backend-engineer | 1.5h |
| T-009-03 | Build student detail page with `p-tabView` | FE | @frontend-engineer | 2h |
| T-009-04 | Build inline edit form with save/cancel | FE | @frontend-engineer | 1.5h |
| T-009-05 | Test: admin edit, student self-edit, parent read-only, forbidden fields | QA | @qa-engineer | 1.5h |

---

### SMS-010: Parent Linking to Student
**Epic:** EPIC-02 | **Points:** 5 | **Priority:** Must

**User Story:**
> As a school admin,
> I want to link a parent user to one or more students,
> So that parents can access their children's data in the Parent Portal.

**Acceptance Criteria:**
- [ ] Given I am admin, When I POST `/api/v1/students/:id/parents`, Then a `student_parent` link is created
- [ ] Given a parent is linked, Then they can see that child in the Parent Portal dashboard
- [ ] Given I link a second parent (e.g., mother + father), Both can access the same child
- [ ] Given I mark one parent as `is_primary_contact=true`, Then that parent is shown as primary
- [ ] Given I remove a parent link, Then that parent loses access to the child's data immediately

**Dependencies:** SMS-003, SMS-007

---

#### Tech Specification — SMS-010

**Backend API:**
```
GET    /api/v1/students/:id/parents          → list linked parents
POST   /api/v1/students/:id/parents          → link parent { "parent_id": 3, "is_primary_contact": true }
DELETE /api/v1/students/:id/parents/:parent_id → unlink parent
Role Required: admin
```

**JWT Enrichment:** When `role=parent` logs in, their `parent_id` is looked up from `parents` table and included in JWT additional_claims.

---

#### Tasks — SMS-010

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-010-01 | Implement `POST /api/v1/students/:id/parents` link endpoint | BE | @backend-engineer | 1.5h |
| T-010-02 | Implement `DELETE /api/v1/students/:id/parents/:pid` unlink | BE | @backend-engineer | 0.5h |
| T-010-03 | Enrich JWT with `parent_id` on login for parent role | BE | @backend-engineer | 1h |
| T-010-04 | Build parent linking UI in student detail Tab 4 | FE | @frontend-engineer | 2h |
| T-010-05 | Test: link, unlink, dual parents, JWT enrichment | QA | @qa-engineer | 1.5h |

---

### SMS-011: Student Transfer Between Sections
**Epic:** EPIC-02 | **Points:** 5 | **Priority:** Should

**User Story:**
> As an admin,
> I want to transfer a student from one section to another,
> So that class sizes can be balanced and students can be reorganized.

**Acceptance Criteria:**
- [ ] Given I POST a transfer, Then the student's current `student_sections` record is closed (end_date set) and a new one opened
- [ ] Given a transfer is made mid-year, Then the old attendance records are preserved under the old section
- [ ] Given I view the student's history, Then I see all section enrollments chronologically

---

#### Tech Specification — SMS-011

**Backend API:**
```
POST /api/v1/students/:id/transfer
Body: { "new_section_id": 7, "effective_date": "2024-03-01", "reason": "Class balancing" }
Role Required: admin
```

**DB Logic:** `student_sections` table has `start_date`, `end_date`, `is_current`. Transfer sets `end_date` on current, creates new record with `is_current=true`.

---

#### Tasks — SMS-011

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-011-01 | Create `student_sections` model with `start_date`, `end_date`, `is_current` | DB | @database-engineer | 1.5h |
| T-011-02 | Implement `StudentService.transfer()` with atomic section swap | BE | @backend-engineer | 2h |
| T-011-03 | Implement `POST /api/v1/students/:id/transfer` route | BE | @backend-engineer | 0.5h |
| T-011-04 | Build transfer dialog in student detail page | FE | @frontend-engineer | 1h |
| T-011-05 | Test: transfer, history preserved, invalid section | QA | @qa-engineer | 1h |

---

### SMS-012: Student Document Upload
**Epic:** EPIC-02 | **Points:** 5 | **Priority:** Should

**User Story:**
> As an admin,
> I want to upload and manage student documents (birth certificate, photo, previous school certificate),
> So that the student's file is complete and accessible digitally.

**Acceptance Criteria:**
- [ ] Given I upload a file, Then it is stored server-side and a URL is returned
- [ ] Allowed file types: PDF, JPG, PNG (max 5MB each)
- [ ] Given wrong file type, Then HTTP 400 with clear error
- [ ] Given I view documents, Then I see a list with file name, type, upload date, download link

---

#### Tech Specification — SMS-012

**Backend API:**
```
POST /api/v1/students/:id/documents
Content-Type: multipart/form-data
Body: { "document_type": "birth_certificate", "file": <binary> }
Response 201: { "data": { "id": 1, "url": "/uploads/students/1/birth_cert.pdf" } }

GET /api/v1/students/:id/documents → list documents
DELETE /api/v1/students/:id/documents/:doc_id
```

**Storage:** Files saved to `backend/uploads/students/<id>/` directory. In production, replace with S3.

**DB:** Add `student_documents` table: `(id, student_id, document_type, file_name, file_path, uploaded_by, created_at)`

---

#### Tasks — SMS-012

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-012-01 | Create `student_documents` model + migration | DB | @database-engineer | 1h |
| T-012-02 | Implement file upload endpoint with type/size validation | BE | @backend-engineer | 2h |
| T-012-03 | Implement document list + delete endpoints | BE | @backend-engineer | 1h |
| T-012-04 | Build document upload tab in student detail with `p-fileUpload` | FE | @frontend-engineer | 2h |
| T-012-05 | Test: valid upload, wrong type, too large, delete | QA | @qa-engineer | 1h |

---

### SMS-013: Student Deactivation / Alumni
**Epic:** EPIC-02 | **Points:** 3 | **Priority:** Could

**User Story:**
> As an admin,
> I want to deactivate a student who has left the school,
> So that they no longer appear in active lists but their records are preserved for audit.

**Acceptance Criteria:**
- [ ] Given I deactivate a student, Then `is_active=false` and they disappear from active lists
- [ ] Given I set `status=alumni`, Then the student appears in an alumni list (not active)
- [ ] Historical records (attendance, grades, fees) remain queryable even after deactivation

---

#### Tech Specification — SMS-013

**Backend API:**
```
DELETE /api/v1/students/:id          → soft-delete (sets is_active=false)
PATCH  /api/v1/students/:id/status   → Body: { "status": "alumni", "leaving_date": "2024-06-30" }
```

**DB:** Add `status` enum column to `students`: `active | alumni | transferred | expelled`

---

#### Tasks — SMS-013

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-013-01 | Add `status` + `leaving_date` to students migration | DB | @database-engineer | 0.5h |
| T-013-02 | Implement `PATCH /api/v1/students/:id/status` | BE | @backend-engineer | 1h |
| T-013-03 | Add deactivation confirmation dialog in UI | FE | @frontend-engineer | 1h |
| T-013-04 | Test: deactivate, alumni status, records still queryable | QA | @qa-engineer | 0.5h |
