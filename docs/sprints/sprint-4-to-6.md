# Sprints 4–6 — Attendance, Grades & Fees
**Scrum Master:** @scrum-master

> **How to invoke agents:**
> - Database work → `@database-engineer` (models, migrations, schema)
> - Backend work → `@backend-engineer` (routes, services, business logic, tests)
> - Frontend work → `@frontend-engineer` (Angular components, PrimeNG UI, HTTP services)

---

# Sprint 4 — Attendance Management
**Sprint Goal:** Enable teachers to mark daily attendance and parents to be notified of absences on the same day.
**Velocity Target:** 29 pts | **Epic:** EPIC-05
**Dependencies:** Sprint 3 (sections + timetable working)

## Sprint Board

| Story | Title | Points | Agents |
|-------|-------|--------|--------|
| SMS-024 | Mark Daily Attendance (Teacher) | 8 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` |
| SMS-025 | Attendance View (Student/Parent) | 5 | `@frontend-engineer` |
| SMS-026 | Attendance Report by Class & Range | 8 | `@backend-engineer` → `@frontend-engineer` |
| SMS-027 | Absence Notification to Parent | 5 | `@backend-engineer` |
| SMS-028 | Attendance Statistics Dashboard | 3 | `@frontend-engineer` |

---

### SMS-024: Mark Daily Attendance (Teacher)

**API:**
```
POST /api/v1/attendance/mark
Role: teacher
Body: {
  "section_id": 5,
  "date": "2026-06-06",
  "records": [
    { "student_id": 1, "status": "present" },
    { "student_id": 2, "status": "absent" },
    { "student_id": 3, "status": "late" }
  ]
}
Response 201: { "message": "Attendance marked for 25 students" }
```

**Business Rules:**
- Only the class teacher of that section (or admin) can mark attendance
- Can only mark attendance for today (admin can backdate up to 7 days)
- Cannot re-mark if already submitted (return 409 with edit option)
- On absent → trigger `NotificationService.create()` for parent

**DB Schema:**
```
attendance: (id, student_id FK, section_id FK, date DATE, status ENUM['present','absent','late','leave','holiday'], marked_by FK→users.id, created_at)
UniqueConstraint(student_id, section_id, date)
```

**Frontend:**
- `/teacher/attendance/mark` — section selector + date + student list with 3-button toggle per row
- PrimeNG `p-selectButton` per student row: Present / Absent / Late
- Bulk "Mark All Present" button at top
- Submit with `p-confirmDialog`

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-024-01 | Create `Attendance` model (`attendance` table) with UniqueConstraint | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-024-02 | Generate + apply migration `add_attendance_table` | [`@database-engineer`](.claude/agents/database-engineer.md) | 0.5h |
| T-024-03 | Implement `AttendanceService.mark_attendance()` with duplicate-check (409) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-024-04 | Implement `POST /api/v1/attendance/mark` — teacher authorization | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-024-05 | Trigger `NotificationService.create()` for each absent student's parents | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-024-06 | Build attendance marking UI (section + date selector, student toggle grid) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 3h |
| T-024-07 | Tests: mark, re-mark 409, teacher auth, absent notification | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |

---

### SMS-025: Attendance View (Student/Parent)

**API:** `GET /api/v1/attendance?student_id=5&month=6&year=2026`
Returns per-day records with status for the given month.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-025-01 | Implement `GET /api/v1/attendance` query with student_id + month/year filter | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-025-02 | Build read-only attendance calendar (color-coded cells by status) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-025-03 | Add month navigation (prev/next without page reload) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-025-04 | Monthly summary row (present/absent/late/percentage) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 0.5h |

---

### SMS-026: Attendance Report by Class & Range

**API:**
```
GET /api/v1/attendance/report?section_id=5&from_date=2026-06-01&to_date=2026-06-30
Response 200: {
  "data": {
    "section": "Grade 5 A",
    "period": "June 2026",
    "students": [
      { "student_id": 1, "name": "Alice", "present": 22, "absent": 2, "late": 1, "percentage": 91.7 }
    ],
    "class_average": 88.5
  }
}
```

**Frontend:** `/admin/attendance/reports` — filterable by section/date range, export to Excel.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-026-01 | Implement attendance aggregation query (group by student, count by status) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-026-02 | Implement `GET /api/v1/attendance/report` with date-range + section filter | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-026-03 | Build filterable report table with export button | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-026-04 | Tests: date range, section filter, empty range | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-027: Absence Notification to Parent

**Logic:** On each absent record in `mark_attendance()`, look up `student_parent` association and call `NotificationService.create(user_id=parent.user_id, type='absence', ...)`.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-027-01 | Create `Notification` model (`notifications` table) + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-027-02 | Implement `NotificationService.create()` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-027-03 | Wire absence trigger into `AttendanceService.mark_attendance()` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-027-04 | Tests: notification created per absent student, multiple parents | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-028: Attendance Statistics Dashboard

**Frontend:** Admin dashboard widget showing today's attendance percentage per section, and school-wide absent/present counts.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-028-01 | Implement `GET /api/v1/attendance/today-summary` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-028-02 | Build dashboard attendance widget with `p-chart` (doughnut) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1.5h |
| T-028-03 | Build section-wise attendance mini-table on dashboard | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |

---

# Sprint 5 — Grade & Exam Management
**Sprint Goal:** Complete exam lifecycle — create exams, enter marks, auto-calculate GPA, and generate printable report cards.
**Velocity Target:** 36 pts | **Epic:** EPIC-06
**Dependencies:** Sprint 4 (attendance working, sections confirmed)

## Sprint Board

| Story | Title | Points | Agents |
|-------|-------|--------|--------|
| SMS-029 | Create Exam Definitions | 5 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` |
| SMS-030 | Subject-wise Marks Entry | 8 | `@backend-engineer` → `@frontend-engineer` |
| SMS-031 | Grade Calculation & GPA | 5 | `@backend-engineer` |
| SMS-032 | Student Report Card Generation | 8 | `@backend-engineer` → `@frontend-engineer` |
| SMS-033 | Class Result Summary | 5 | `@frontend-engineer` |
| SMS-034 | Marks Edit & Approval Workflow | 5 | `@backend-engineer` |

---

### SMS-029: Create Exam Definitions

**DB Schema:**
```
exams: (id, name, term, exam_type ENUM['midterm','final','unit_test','practical'],
        section_id FK, conducted_date DATE, academic_year_id FK, is_active)
```

**API:**
```
POST /api/v1/exams     → create exam (admin)
GET  /api/v1/exams     → list exams (admin + teacher, filter by section_id)
GET  /api/v1/exams/:id → single exam
PUT  /api/v1/exams/:id → update (admin)
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-029-01 | Create `Exam` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-029-02 | Implement `ExamService` CRUD | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-029-03 | Implement exam routes blueprint | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-029-04 | Build exam list + create/edit dialog (admin) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-029-05 | Tests: create, list by section, teacher sees only own sections | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-030: Subject-wise Marks Entry

**API:**
```
POST /api/v1/exams/:exam_id/marks
Role: teacher (own subjects only), admin
Body: {
  "subject_id": 3,
  "section_id": 5,
  "marks": [
    { "student_id": 1, "marks_obtained": 82 },
    { "student_id": 2, "marks_obtained": 45 }
  ]
}
```

**DB Schema:**
```
exam_results: (id, exam_id FK, student_id FK, subject_id FK,
               marks_obtained NUMERIC(5,2), grade VARCHAR(2), gpa NUMERIC(3,2),
               created_by FK→users.id, status ENUM['draft','finalized'])
UniqueConstraint(exam_id, student_id, subject_id)
```

**Business Rules:**
- `marks_obtained` ≤ subject's `max_marks`
- Teacher can only enter marks for subjects they're assigned to (`teacher_subjects`)
- Marks entry locked once `status=finalized`
- On save: auto-calculate grade + GPA

**Grade Scale:**
| Percentage | Grade | GPA |
|-----------|-------|-----|
| 90–100 | A+ | 4.0 |
| 80–89 | A | 3.7 |
| 70–79 | B | 3.0 |
| 60–69 | C | 2.3 |
| 50–59 | D | 1.7 |
| 40–49 | E | 1.0 |
| <40 | F | 0.0 |

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-030-01 | Create `ExamResult` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-030-02 | Implement `ExamService.calculate_grade(marks, max_marks)` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-030-03 | Implement `ExamService.enter_marks()` with teacher subject restriction + max_marks check | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-030-04 | Implement `POST /api/v1/exams/:id/marks` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-030-05 | Build marks entry grid (student rows × subject per exam) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 3h |
| T-030-06 | Tests: marks entry, max_marks violation, finalized lock, teacher restriction | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |

---

### SMS-031: Grade Calculation & GPA

**Logic:** `ExamService.calculate_grade()` runs on every marks save. Overall GPA = average of all subject GPAs in an exam.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-031-01 | Implement per-subject grade/GPA calculation in `ExamService` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-031-02 | Implement overall GPA aggregation for a student × exam | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-031-03 | `GET /api/v1/exams/:id/results?student_id=N` — return subject breakdown + overall GPA | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-031-04 | Tests: grade boundaries (A+/A/B/F edge cases), GPA average | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-032: Student Report Card Generation

**API:**
```
GET /api/v1/exams/:exam_id/report-card/:student_id
Response: PDF (application/pdf)
Content-Disposition: attachment; filename="report_card_Alice_Midterm2026.pdf"
```

**PDF includes:** school header, student info, subject-wise marks table, total/percentage/grade/GPA, signature lines.
**Library:** `WeasyPrint` (HTML→PDF) or `ReportLab`.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-032-01 | Add `WeasyPrint` to `requirements.txt` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.25h |
| T-032-02 | Create HTML report card template (`templates/report_card.html`) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-032-03 | Implement `ExamService.generate_report_card_pdf(exam_id, student_id)` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-032-04 | Implement `GET /api/v1/exams/:id/report-card/:student_id` route | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-032-05 | Wire "Download Report Card" button in student detail view | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 0.5h |
| T-032-06 | Tests: PDF generated, correct student data, wrong student 403 | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-033: Class Result Summary

**Frontend:** Admin/teacher view of all students' results for an exam — sortable table with grade column, class average, pass/fail count.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-033-01 | `GET /api/v1/exams/:id/results` — all students, all subjects | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-033-02 | Build class result summary table with sorting and colour-coded grades | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-033-03 | Add subject-wise bar chart (`p-chart`) below the table | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-033-04 | Add pass/fail count summary cards above the table | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 0.5h |

---

### SMS-034: Marks Edit & Approval Workflow

**API:**
```
PUT /api/v1/exams/:exam_id/results/:result_id   → edit marks (draft only)
PUT /api/v1/exams/:exam_id/finalize             → admin locks all marks
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-034-01 | Implement `ExamService.update_marks()` — blocked if `status=finalized` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-034-02 | Implement `ExamService.finalize_exam()` — bulk status update | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-034-03 | Implement `PUT /api/v1/exams/:id/finalize` (admin only) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-034-04 | Add "Finalize Exam" button to marks entry UI (admin only) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 0.5h |
| T-034-05 | Tests: edit draft OK, edit finalized 409, finalize endpoint | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

# Sprint 6 — Fee Management
**Sprint Goal:** Define fee structures, generate student obligations, record payments, and produce receipts — enabling the school to manage finances efficiently.
**Velocity Target:** 33 pts | **Epic:** EPIC-07
**Dependencies:** Sprint 2 (students), Sprint 3 (classes)

## Sprint Board

| Story | Title | Points | Agents |
|-------|-------|--------|--------|
| SMS-035 | Fee Structure per Class | 5 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` |
| SMS-036 | Generate Student Fee Records | 5 | `@backend-engineer` |
| SMS-037 | Record Fee Payment | 8 | `@backend-engineer` → `@frontend-engineer` |
| SMS-038 | Fee Receipt PDF Generation | 5 | `@backend-engineer` |
| SMS-039 | Fee Arrears & Defaulter Report | 5 | `@backend-engineer` → `@frontend-engineer` |
| SMS-040 | Discount & Scholarship Management | 5 | `@backend-engineer` |

---

### SMS-035: Fee Structure per Class

**DB Schema:**
```
fee_structures: (id, class_id FK, fee_type VARCHAR(100), amount NUMERIC(10,2),
                 due_date DATE, academic_year_id FK, is_recurring BOOL,
                 frequency ENUM['monthly','quarterly','annual','one_time'], is_active)
```

**API:**
```
POST /api/v1/fee-structures     → create (admin)
GET  /api/v1/fee-structures     → list (filter by class_id, academic_year_id)
PUT  /api/v1/fee-structures/:id → update
DELETE /api/v1/fee-structures/:id → soft delete
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-035-01 | Create `FeeStructure` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-035-02 | Implement `FeeStructureService` CRUD | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-035-03 | Implement fee-structure routes blueprint | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-035-04 | Build fee structure list + add/edit dialog per class | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-035-05 | Tests: create, list by class, update, soft delete | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-036: Generate Student Fee Records

**Logic:** When a fee structure is created or a student enrolls, generate individual `fee_records` for each enrolled student.

**DB Schema:**
```
fee_records: (id, student_id FK, fee_structure_id FK, amount NUMERIC(10,2),
              discount NUMERIC(10,2) default 0, net_amount NUMERIC(10,2),
              due_date DATE, status ENUM['pending','paid','partial','waived'])
UniqueConstraint(student_id, fee_structure_id)
```

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-036-01 | Create `FeeRecord` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-036-02 | Implement `FeeService.generate_records_for_class(class_id, fee_structure_id)` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-036-03 | Implement `POST /api/v1/fee-structures/:id/generate` (admin) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-036-04 | Tests: generate for class, skip already-generated, partial class | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-037: Record Fee Payment

**API:**
```
POST /api/v1/fees/payments
Role: admin
Body: {
  "fee_record_id": 15,
  "amount_paid": 5000.00,
  "payment_method": "cash"|"bank_transfer"|"cheque"|"online",
  "payment_date": "2026-06-06",
  "transaction_reference": "TXN12345",
  "remarks": "June fee"
}
Response 201: {
  "data": {
    "payment_id": 201,
    "receipt_no": "REC-2026-0201",
    "amount_paid": 5000.00,
    "balance_due": 0.00
  }
}
```

**DB Schema:**
```
fee_payments: (id, fee_record_id FK, amount_paid NUMERIC(10,2), payment_method,
               payment_date DATE, receipt_no VARCHAR(20) UNIQUE,
               transaction_reference, collected_by FK→users.id, created_at)
```

**Receipt Number:** Auto-generated `REC-YYYY-NNNN` (sequential per year).

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-037-01 | Create `FeePayment` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-037-02 | Implement `FeeService.record_payment()` — receipt no. generation + balance calculation | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-037-03 | Implement `POST /api/v1/fees/payments` route | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-037-04 | Build fee payment form (search student → select fee record → enter payment) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-037-05 | Build student fee ledger view (all records with status badges) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1.5h |
| T-037-06 | Tests: payment, partial payment, overpayment check | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |

---

### SMS-038: Fee Receipt PDF Generation

**API:**
```
GET /api/v1/fees/payments/:id/receipt
Response: PDF (application/pdf)
```

**PDF includes:** school header, student name, fee type, amount paid, payment method, receipt number, date, cashier signature.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-038-01 | Create HTML receipt template (`templates/fee_receipt.html`) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-038-02 | Implement `FeeService.generate_receipt_pdf(payment_id)` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-038-03 | Implement `GET /api/v1/fees/payments/:id/receipt` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-038-04 | Wire "Download Receipt" button in fee ledger UI | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 0.5h |
| T-038-05 | Tests: PDF generated, correct receipt data, wrong payment 403 | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-039: Fee Arrears & Defaulter Report

**API:**
```
GET /api/v1/fees/defaulters?class_id=3&as_of_date=2026-06-06
Response: students with outstanding dues > 30 days overdue
```

**Frontend:** Exportable table with: student name, class, outstanding amount, days overdue, last payment date.
**Notification:** Trigger `NotificationService.create()` for parent when fee becomes 7 days overdue.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-039-01 | Implement `FeeService.get_defaulters(class_id, as_of_date)` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-039-02 | Implement `GET /api/v1/fees/defaulters` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-039-03 | Trigger overdue notification at 7-day mark | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-039-04 | Build defaulter report table with export button | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-039-05 | Tests: overdue logic, class filter, notification trigger | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |

---

### SMS-040: Discount & Scholarship Management

**API:**
```
POST /api/v1/fee-records/:id/discount
Body: { "discount_type": "scholarship"|"sibling"|"staff", "amount": 500.00, "reason": "Merit scholarship" }
```

**Logic:** Updates `fee_records.discount` and recalculates `net_amount = amount - discount`.

#### Tasks

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-040-01 | Implement `FeeService.apply_discount(fee_record_id, discount_type, amount, reason)` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-040-02 | Implement `POST /api/v1/fee-records/:id/discount` (admin) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-040-03 | Add discount amount field to fee ledger view | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-040-04 | Tests: discount applied, net_amount updated, over-discount blocked | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
