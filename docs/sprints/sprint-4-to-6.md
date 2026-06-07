# Sprints 4–6 — Attendance, Grades & Fees
**Scrum Master:** @scrum-master

---

# Sprint 4 — Attendance Management
**Sprint Goal:** Enable teachers to mark daily attendance and parents to be notified of absences on the same day.
**Velocity Target:** 29 pts | **Epic:** EPIC-05
**Dependencies:** Sprint 3 (sections + timetable working)

## Sprint Board

| Story | Title | Points | Assignee |
|-------|-------|--------|----------|
| SMS-024 | Mark Daily Attendance (Teacher) | 8 | @backend-engineer + @frontend-engineer |
| SMS-025 | Attendance View (Student/Parent) | 5 | @frontend-engineer |
| SMS-026 | Attendance Report by Class & Range | 8 | @backend-engineer + @frontend-engineer |
| SMS-027 | Absence Notification to Parent | 5 | @backend-engineer |
| SMS-028 | Attendance Statistics Dashboard | 3 | @frontend-engineer |

---

### SMS-024: Mark Daily Attendance (Teacher) — Tech Spec

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

**DB:** `attendance` table: `(id, student_id, section_id, date, status['present','absent','late','leave','holiday'], marked_by, created_at)`

**Frontend:**
- `/teacher/attendance/mark` — section selector + date + student list with 3-button toggle per row
- PrimeNG `p-selectButton` per student row: Present / Absent / Late
- Bulk "Mark All Present" button at top
- Submit with `p-confirmDialog`

**Tasks:**
| Task | Est. |
|------|------|
| Create `attendance` model + migration | 1h |
| Implement `AttendanceService.mark_attendance()` with conflict check | 2h |
| Implement `POST /api/v1/attendance/mark` with teacher authorization | 1h |
| Trigger parent notification for each absent student | 1h |
| Build attendance marking UI (student list with toggles) | 3h |
| Test: mark attendance, re-mark conflict, teacher authorization, notifications | 2h |

---

### SMS-026: Attendance Report by Class & Range — Tech Spec

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

**Frontend:** `/admin/attendance/reports` — filterable by section/date range, exported to Excel.

**Tasks:**
| Task | Est. |
|------|------|
| Implement attendance aggregation query | 2h |
| Implement report endpoint with date range filter | 1h |
| Build report table with export button | 2h |
| Test: date range, section filter, export | 1.5h |

---

# Sprint 5 — Grade & Exam Management
**Sprint Goal:** Complete exam lifecycle — create exams, enter marks, auto-calculate GPA, and generate printable report cards.
**Velocity Target:** 36 pts | **Epic:** EPIC-06
**Dependencies:** Sprint 4 (attendance working, sections confirmed)

## Sprint Board

| Story | Title | Points | Assignee |
|-------|-------|--------|----------|
| SMS-029 | Create Exam Definitions | 5 | @backend-engineer + @frontend-engineer |
| SMS-030 | Subject-wise Marks Entry | 8 | @backend-engineer + @frontend-engineer |
| SMS-031 | Grade Calculation & GPA | 5 | @backend-engineer |
| SMS-032 | Student Report Card Generation | 8 | @backend-engineer + @frontend-engineer |
| SMS-033 | Class Result Summary | 5 | @frontend-engineer |
| SMS-034 | Marks Edit & Approval Workflow | 5 | @backend-engineer |

---

### SMS-030: Subject-wise Marks Entry — Tech Spec

**API:**
```
POST /api/v1/exams/:exam_id/marks
Role: teacher (for own subjects), admin
Body: {
  "subject_id": 3,
  "section_id": 5,
  "marks": [
    { "student_id": 1, "marks_obtained": 82 },
    { "student_id": 2, "marks_obtained": 45 }
  ]
}
```

**Business Rules:**
- `marks_obtained` ≤ subject's `max_marks`
- Teacher can only enter marks for subjects they're assigned to
- Marks entry is locked once approved by admin (`status=finalized`)
- On save: calculate grade + GPA per student, store in `exam_results`

**Grade Scale (configurable):**
| Percentage | Grade | GPA |
|-----------|-------|-----|
| 90–100 | A+ | 4.0 |
| 80–89 | A | 3.7 |
| 70–79 | B | 3.0 |
| 60–69 | C | 2.3 |
| 50–59 | D | 1.7 |
| 40–49 | E | 1.0 |
| <40 | F | 0.0 |

**DB:**
- `exams`: `(id, name, term, exam_type['midterm','final','unit'], section_id, conducted_date, academic_year_id)`
- `exam_results`: `(id, exam_id, student_id, subject_id, marks_obtained, grade, gpa, created_by, status['draft','finalized'])`

**Tasks:**
| Task | Est. |
|------|------|
| Create `exams` + `exam_results` models + migration | 1.5h |
| Implement grade calculation logic in `ExamService` | 2h |
| Implement marks entry endpoint with teacher authorization | 1.5h |
| Build marks entry grid UI (student rows × subject columns) | 3h |
| Test: marks entry, max marks violation, teacher subject restriction | 2h |

---

### SMS-032: Student Report Card Generation — Tech Spec

**API:**
```
GET /api/v1/exams/:exam_id/report-card/:student_id
Response: PDF file (application/pdf)
Headers: Content-Disposition: attachment; filename="report_card_Alice_Midterm2026.pdf"
```

**PDF Generation:** Use `WeasyPrint` or `ReportLab` library. Template includes:
- School header (name, logo, address)
- Student info (name, admission_no, class, section, roll_no)
- Subject-wise marks table with grade column
- Total marks, percentage, overall grade, GPA
- Teacher and Principal signature lines

**Tasks:**
| Task | Est. |
|------|------|
| Implement PDF generation with WeasyPrint | 3h |
| Create HTML report card template | 2h |
| Implement report card download endpoint | 1h |
| Test: PDF content correctness, download, multi-student | 1.5h |

---

# Sprint 6 — Fee Management
**Sprint Goal:** Complete fee lifecycle — define structures, generate student obligations, record payments, and produce receipts — enabling the school to manage finances efficiently.
**Velocity Target:** 33 pts | **Epic:** EPIC-07
**Dependencies:** Sprint 2 (students), Sprint 3 (classes)

## Sprint Board

| Story | Title | Points | Assignee |
|-------|-------|--------|----------|
| SMS-035 | Fee Structure per Class | 5 | @backend-engineer + @frontend-engineer |
| SMS-036 | Generate Student Fee Records | 5 | @backend-engineer |
| SMS-037 | Record Fee Payment | 8 | @backend-engineer + @frontend-engineer |
| SMS-038 | Fee Receipt PDF Generation | 5 | @backend-engineer |
| SMS-039 | Fee Arrears & Defaulter Report | 5 | @backend-engineer + @frontend-engineer |
| SMS-040 | Discount & Scholarship Management | 5 | @backend-engineer |

---

### SMS-037: Record Fee Payment — Tech Spec

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

**DB:**
- `fee_structures`: `(id, class_id, fee_type, amount, due_date, academic_year_id, is_recurring, frequency)`
- `fee_records`: `(id, student_id, fee_structure_id, amount, discount, net_amount, due_date, status)`
- `fee_payments`: `(id, fee_record_id, amount_paid, payment_method, payment_date, receipt_no, transaction_reference, collected_by)`

**Receipt Number:** Auto-generated `REC-YYYY-NNNN` (sequential per year)

**Tasks:**
| Task | Est. |
|------|------|
| Create fee models + migrations (3 tables) | 2h |
| Implement `FeeService.record_payment()` with receipt number generation | 2h |
| Implement payment endpoint | 1h |
| Build fee payment form in admin UI | 2h |
| Implement PDF receipt generation | 2h |
| Test: payment, partial payment, overpayment check | 1.5h |

---

### SMS-039: Fee Arrears & Defaulter Report — Tech Spec

**API:**
```
GET /api/v1/fees/defaulters?class_id=3&as_of_date=2026-06-06
Response: list of students with outstanding dues > 30 days overdue
```

**Frontend:** Exportable table with student name, class, outstanding amount, days overdue, last payment date.

**Notification integration:** Trigger `NotificationService.create()` for parent when fee becomes 7 days overdue.
