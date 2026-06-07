# SMS — Complete API Reference
**Base URL:** `http://localhost:5000/api/v1`
**Auth:** `Authorization: Bearer <access_token>` on all protected routes
**Content-Type:** `application/json`

---

## Standard Response Envelope

```json
{
  "success": true | false,
  "data": { } | [ ] | null,
  "message": "Human readable message",
  "errors": null | { "field": ["error msg"] }
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request (missing/malformed body) |
| 401 | Unauthorized (no/invalid/expired token) |
| 403 | Forbidden (valid token, wrong role or wrong resource) |
| 404 | Not Found |
| 409 | Conflict (duplicate unique field) |
| 422 | Unprocessable Entity (validation errors) |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

### Pagination Query Params
```
?page=1&per_page=20
```
Paginated responses include a `meta` object:
```json
"meta": { "total": 150, "page": 1, "per_page": 20, "pages": 8 }
```

---

## 1. Authentication — `/api/v1/auth`

### POST `/auth/login`
**Public** | Rate limit: 5/minute

```json
// Request
{ "email": "admin@school.com", "password": "SecurePass123" }

// Response 200
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "user": { "id": 1, "email": "admin@school.com", "role": "admin" }
  }
}
// Response 401 — invalid credentials
// Response 429 — rate limited
```

### POST `/auth/refresh`
**Requires:** refresh_token in Authorization header

```json
// Response 200
{ "data": { "access_token": "eyJ..." } }
```

### POST `/auth/logout`
**Requires:** access_token

```json
// Request
{ "refresh_token": "eyJ..." }
// Response 200 — both tokens revoked
```

### GET `/auth/me`
**Requires:** any role

```json
// Response 200
{
  "data": { "id": 1, "email": "admin@school.com", "role": "admin",
            "is_active": true, "created_at": "2026-06-06T10:00:00" }
}
```

### PATCH `/auth/profile`
**Requires:** any role (own profile only)

```json
// Request — updatable fields only (NOT email, NOT role)
{ "first_name": "John", "phone": "9876543210", "address": "123 Main St" }
// Response 200
```

### POST `/auth/forgot-password` — Public
```json
// Request
{ "email": "user@school.com" }
// Response 200 — always (no email enumeration)
{ "message": "If this email exists, a reset link has been sent" }
```

### POST `/auth/reset-password` — Public
```json
// Request
{ "token": "abc123...", "new_password": "NewPass@123" }
// Response 200 | 400 (expired/used token) | 422 (weak password)
```

---

## 2. Users — `/api/v1/users`
**Requires:** admin

### POST `/users` — Create user
```json
// Request
{
  "email": "teacher1@school.com",
  "password": "TempPass@123",
  "role": "teacher",
  "first_name": "Priya",
  "last_name": "Sharma"
}
// Response 201 — creates user + auto-profile (Teacher/Parent record)
// Response 409 — email already exists
```

### GET `/users` — List users
```
?role=teacher&page=1&per_page=20
```

### GET `/users/:id` | PUT `/users/:id` | DELETE `/users/:id`

---

## 3. Students — `/api/v1/students`

### GET `/students`
**Requires:** admin, teacher
```
?page=1&per_page=20&search=alice&class_id=3&section_id=5&status=active
```

### POST `/students`
**Requires:** admin
```json
{
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
// Response 201 | 409 (duplicate admission_no) | 422 (validation)
```

### GET `/students/:id`
**Requires:** admin, teacher (own student), student (own record), parent (via parent portal — not this endpoint)

### PUT `/students/:id`
**Requires:** admin (all fields) | student (phone, address only — own record)

### DELETE `/students/:id`
**Requires:** admin — soft deletes (sets is_active=false)

### PATCH `/students/:id/status`
**Requires:** admin
```json
{ "status": "alumni", "leaving_date": "2024-06-30" }
```

### POST `/students/:id/transfer`
**Requires:** admin
```json
{ "new_section_id": 7, "effective_date": "2024-03-01", "reason": "Class balancing" }
```

### GET `/students/:id/parents` | POST `/students/:id/parents` | DELETE `/students/:id/parents/:parent_id`
**Requires:** admin
```json
// POST body
{ "parent_id": 3, "is_primary_contact": true }
```

### POST `/students/:id/documents`
**Requires:** admin — multipart/form-data
```
document_type: birth_certificate | transfer_certificate | photo | medical | other
file: <binary>
Max size: 5MB | Allowed: PDF, JPG, PNG
```

---

## 4. Teachers — `/api/v1/teachers`

### POST `/teachers`
**Requires:** admin
```json
{
  "employee_id": "EMP001",
  "first_name": "Priya",
  "last_name": "Sharma",
  "date_of_birth": "1985-08-20",
  "gender": "Female",
  "qualification": "B.Ed, M.Sc Mathematics",
  "joining_date": "2020-06-01",
  "phone": "9988776655",
  "user_id": 10
}
```

### GET `/teachers` — `?search=priya` | **Requires:** admin
### GET `/teachers/:id` — **Requires:** admin, teacher (own)
### PUT `/teachers/:id` — **Requires:** admin
### DELETE `/teachers/:id` — **Requires:** admin

### GET `/teachers/:id/schedule`
**Requires:** admin, teacher (own)
```json
// Response
{ "data": { "teacher_id": 2, "schedule": [
  { "day": "Monday", "period": 1, "subject": "Mathematics", "section": "Grade 5 A",
    "start_time": "08:00", "end_time": "08:45" }
]}}
```

### POST `/teachers/:id/subjects`
**Requires:** admin
```json
{ "subject_ids": [1, 3, 5] }
```

---

## 5. Classes & Sections — `/api/v1/classes`, `/api/v1/sections`

### GET/POST/PUT/DELETE `/classes`
**Requires:** admin
```json
// POST body
{ "name": "Grade 5", "grade_level": 5, "academic_year_id": 1 }
```

### GET/POST/PUT/DELETE `/sections`
**Requires:** admin
```json
// POST body
{ "class_id": 3, "name": "A", "capacity": 35, "class_teacher_id": 7 }
```

### POST `/sections/:id/enroll`
**Requires:** admin
```json
{ "student_ids": [1, 2, 3, 4] }
```

### GET/POST/PUT/DELETE `/timetables`
**Requires:** admin (write), admin+teacher (read)
```json
// POST body
{ "section_id": 5, "subject_id": 2, "teacher_id": 7,
  "day_of_week": 1, "period_no": 1, "start_time": "08:00", "end_time": "08:45" }
// Error 409 if teacher or section slot already occupied
```

---

## 6. Attendance — `/api/v1/attendance`

### POST `/attendance/mark`
**Requires:** teacher (own section), admin
```json
{
  "section_id": 5,
  "date": "2026-06-06",
  "records": [
    { "student_id": 1, "status": "present" },
    { "student_id": 2, "status": "absent", "remarks": "No reason given" },
    { "student_id": 3, "status": "late" }
  ]
}
// Response 201 | 409 (already marked for this date — returns edit_url)
```

### GET `/attendance`
**Requires:** admin, teacher
```
?section_id=5&date=2026-06-06
?student_id=3&from_date=2026-06-01&to_date=2026-06-30
```

### GET `/attendance/report`
**Requires:** admin, teacher
```
?section_id=5&from_date=2026-06-01&to_date=2026-06-30
```
```json
// Response
{ "data": { "section": "Grade 5 A", "students": [
  { "student_id": 1, "name": "Alice", "present": 22, "absent": 2, "late": 1, "percentage": 91.7 }
], "class_average": 88.5 }}
```

### GET `/attendance/report/export?format=pdf|excel&...`
**Requires:** admin, teacher — returns file download

---

## 7. Exams & Grades — `/api/v1/exams`

### POST `/exams`
**Requires:** admin
```json
{ "name": "Midterm 2026", "term": "Term 1", "exam_type": "midterm",
  "section_id": 5, "academic_year_id": 1, "conducted_date": "2026-03-15" }
```

### GET `/exams` — `?section_id=5&academic_year_id=1` | **Requires:** admin, teacher

### POST `/exams/:id/marks`
**Requires:** teacher (assigned subject), admin
```json
{
  "subject_id": 3,
  "section_id": 5,
  "marks": [
    { "student_id": 1, "marks_obtained": 82 },
    { "student_id": 2, "marks_obtained": 45 }
  ]
}
// Response 201 | 422 (marks > max_marks)
```

### GET `/exams/:id/results`
**Requires:** admin, teacher
```json
// Response — class-wide results for this exam
{ "data": { "exam": {...}, "results": [
  { "student": {...}, "subjects": [
    { "subject": "Math", "marks_obtained": 82, "max_marks": 100, "grade": "A", "gpa": 3.7 }
  ], "total": 82, "percentage": 82.0, "gpa": 3.7, "overall_grade": "A" }
]}}
```

### GET `/exams/:exam_id/report-card/:student_id`
**Requires:** admin, teacher, student (own), parent (via parent portal)
**Response:** PDF file download

### PUT `/exams/:id/marks/:result_id` — Edit marks
**Requires:** admin only (teacher marks locked after 24h)

### POST `/exams/:id/finalize`
**Requires:** admin — locks all marks for this exam

---

## 8. Fees — `/api/v1/fees`

### GET/POST/PUT/DELETE `/fees/structures`
**Requires:** admin
```json
// POST body
{ "class_id": 3, "fee_type": "Tuition Fee", "amount": 5000.00,
  "due_day": 15, "academic_year_id": 1, "frequency": "monthly" }
```

### POST `/fees/generate`
**Requires:** admin — bulk generate fee records for a class
```json
{ "class_id": 3, "academic_year_id": 1, "month": 6, "year": 2026 }
// Creates fee_records for all active students in class
```

### GET `/fees/records`
**Requires:** admin
```
?student_id=5&status=pending&class_id=3
```

### POST `/fees/payments`
**Requires:** admin
```json
{
  "fee_record_id": 15,
  "amount_paid": 5000.00,
  "payment_method": "cash",
  "payment_date": "2026-06-06",
  "transaction_reference": "TXN12345",
  "remarks": "June tuition"
}
// Response 201 — { "payment_id": 201, "receipt_no": "REC-2026-0201", "balance_due": 0.00 }
```

### GET `/fees/payments/:id/receipt`
**Requires:** admin, parent (own child — via parent portal)
**Response:** PDF receipt download

### GET `/fees/defaulters`
**Requires:** admin
```
?class_id=3&as_of_date=2026-06-06&days_overdue=30
```

### PATCH `/fees/records/:id/discount`
**Requires:** admin
```json
{ "discount": 1000.00, "reason": "Merit scholarship" }
```

---

## 9. Parent Portal — `/api/v1/parent-portal`
**All routes require:** `role=parent` in JWT

### GET `/parent-portal/dashboard`
```json
{
  "data": {
    "parent": { "id": 1, "first_name": "John", "last_name": "Doe" },
    "children": [{
      "student": { "id": 5, "first_name": "Alice", "class": "Grade 5 A" },
      "attendance_summary": { "month": 6, "year": 2026, "present": 18, "absent": 2, "percentage": 90.0 },
      "pending_fees": { "total_due": 5000.00, "overdue_count": 1 },
      "recent_grades": { "exam": "Midterm 2026", "average_marks": 82.5, "grade": "A" }
    }],
    "unread_notifications": 3
  }
}
```

### GET `/parent-portal/children`
```json
{ "data": { "children": [{ "id": 5, "first_name": "Alice", ... }] } }
```

### GET `/parent-portal/children/:id/attendance?month=6&year=2026`
```json
{
  "data": {
    "records": [{ "date": "2026-06-01", "status": "present" }],
    "summary": { "present": 18, "absent": 2, "late": 1, "percentage": 90.0 }
  }
}
```

### GET `/parent-portal/children/:id/grades`
```json
{
  "data": { "exams": [{
    "exam_name": "Midterm 2026",
    "subjects": [{ "subject": "Math", "marks_obtained": 82, "max_marks": 100, "grade": "A", "pass": true }],
    "percentage": 82.0, "gpa": 3.7, "overall_grade": "A"
  }]}
}
```

### GET `/parent-portal/children/:id/fees`
```json
{
  "data": {
    "total_due": 5000.00, "total_paid": 12000.00,
    "records": [{ "fee_type": "Tuition", "amount": 5000.00, "due_date": "2026-06-15", "status": "pending" }]
  }
}
```

### GET `/parent-portal/notices?page=1&per_page=10`

---

## 10. Leave Applications — `/api/v1/leave-applications`

### POST `/leave-applications`
**Requires:** parent
```json
{
  "student_id": 5,
  "from_date": "2026-06-10",
  "to_date": "2026-06-11",
  "leave_type": "sick",
  "reason": "Child has fever and doctor advised rest"
}
// Response 201 | 422 (past date, end before start) | 403 (student not linked)
```

### GET `/leave-applications`
**Requires:** parent (own) | admin/teacher (all, filterable)
```
?status=pending&student_id=5
```

### PUT `/leave-applications/:id/review`
**Requires:** admin, teacher
```json
{ "status": "approved" | "rejected", "remarks": "Doctor certificate required" }
// On approve: attendance records for date range marked as 'leave'
// Triggers notification to parent
```

---

## 11. Notifications — `/api/v1/notifications`

### GET `/notifications`
**Requires:** any role (own notifications only)
```
?unread=true
```
```json
{ "data": { "notifications": [{
  "id": 1, "type": "absence", "title": "Alice marked absent",
  "body": "Your child Alice was marked absent on 2026-06-06",
  "reference_id": 5, "reference_type": "attendance",
  "is_read": false, "created_at": "2026-06-06T09:30:00"
}]}}
```

### PUT `/notifications/:id/read` | **Requires:** any role
### PUT `/notifications/read-all` | **Requires:** any role

---

## 12. Messages — `/api/v1/messages`

### GET `/messages/threads`
**Requires:** parent, teacher — own threads only
```json
{ "data": { "threads": [{
  "id": "uuid", "subject": "About homework",
  "last_message_at": "2026-06-06T14:00:00",
  "unread_count": 2
}]}}
```

### POST `/messages/threads`
**Requires:** parent
```json
{ "child_id": 5, "subject": "About homework", "message": "Hi teacher, Alice didn't understand..." }
// Auto-resolves class teacher from child's current section
```

### GET `/messages/threads/:id`
```json
{ "data": { "thread": {...}, "messages": [
  { "id": 1, "sender_id": 42, "body": "Hi teacher...", "is_read": true, "created_at": "..." },
  { "id": 2, "sender_id": 10, "body": "Hello, Alice did great...", "is_read": false }
]}}
```

### POST `/messages/threads/:id/reply`
**Requires:** parent or teacher (must be in the thread)
```json
{ "message": "Thank you for your reply!" }
```

### PUT `/messages/threads/:id/read` — Mark all messages in thread as read

---

## 13. Announcements — `/api/v1/announcements`

### POST `/announcements`
**Requires:** admin
```json
{
  "title": "Parent-Teacher Meeting",
  "content": "PTM scheduled for June 15...",
  "target_roles": ["parent", "student"],
  "target_class_ids": [3, 4],
  "publish_at": "2026-06-07T08:00:00",
  "expires_at": "2026-06-20T23:59:59"
}
```

### GET `/announcements` — `?status=published` | **Requires:** any role (filtered by own role + class)
### PUT `/announcements/:id` | DELETE `/announcements/:id` — **Requires:** admin

---

## 14. Library — `/api/v1/library`

### GET/POST/PUT/DELETE `/library/books`
**Requires:** admin (write), any (read)
```json
// POST body
{ "isbn": "978-0-13-110362-7", "title": "The C Programming Language",
  "author": "Kernighan & Ritchie", "category": "Computer Science", "total_copies": 3 }
```

### POST `/library/issue`
**Requires:** admin
```json
{ "book_id": 10, "student_id": 5, "due_date": "2026-06-20" }
```

### PUT `/library/issue/:id/return`
**Requires:** admin
```json
{ "returned_date": "2026-06-18" }
// Response: { "fine_amount": 0 }
```

### GET `/library/overdue` — **Requires:** admin

---

## 15. Transport — `/api/v1/transport`

### GET/POST/PUT/DELETE `/transport/routes` — **Requires:** admin
### GET/POST/PUT/DELETE `/transport/vehicles` — **Requires:** admin
### POST `/transport/assign`
**Requires:** admin
```json
{ "student_id": 5, "route_id": 2, "pickup_stop": "Main Gate", "drop_stop": "City Park" }
```

---

## 16. Reports & Dashboard — `/api/v1/dashboard`, `/api/v1/reports`

### GET `/dashboard/admin` — **Requires:** admin
```json
{ "data": {
  "total_students": 1250, "total_teachers": 48,
  "attendance_today": { "present": 1100, "absent": 150, "percentage": 88.0 },
  "fee_collection_this_month": { "collected": 850000, "pending": 120000 },
  "pending_leave_applications": 12,
  "fee_defaulters_count": 23
}}
```

### GET `/reports/attendance/export?format=pdf|excel&section_id=5&from_date=...&to_date=...`
### GET `/reports/grades/export?format=pdf|excel&exam_id=3`
### GET `/reports/fees/export?format=pdf|excel&class_id=3&as_of_date=...`
**All require:** admin — returns file download

---

## Parents (Admin Management) — `/api/v1/parents`

### GET `/parents` — `?search=john` | **Requires:** admin
### GET `/parents/:id` | PUT `/parents/:id` — **Requires:** admin
### GET `/parents/me` | PATCH `/parents/me` — **Requires:** parent (own profile)
### POST `/parents/me/photo` — **Requires:** parent — multipart/form-data
