# SMS — Complete Database Schema
**Author:** @database-engineer | **Date:** 2026-06-06 (rev. 2026-06-24)
**Database:** PostgreSQL (runtime) · in-memory SQLite for the `TESTING` unit suite

---

## Physical Layout — Schema-per-School Multi-Tenancy

The platform runs on **one PostgreSQL database** with a **schema per school**
(see [ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md) and
[ADR-004](adr-004-postgresql-schema-per-school.md)).

```
PostgreSQL database
├── public                 ← MASTER REGISTRY (created at app startup)
│     ├── schools                      (id, name, slug, db_url=schema name, is_active, …)
│     ├── super_admins                 (id, email, password_hash, …)
│     └── super_admin_revoked_tokens   (id, jti, …)
│
└── school_<slug>          ← ONE PER SCHOOL (created at provision time)
      ├── <all tables documented below>   (~34 tables: users, students, …)
      └── alembic_version                 (this school's migration head)
```

- **Master tables** (`schools`, `super_admins`, `super_admin_revoked_tokens`)
  carry `__bind_key__='master'` and live in `public`. They are created via
  `db.create_all(bind_key=['master'])` at startup, **not** by Alembic.
- **All other tables** (the ERD below) are **school-scoped**: an identical set
  exists inside every `school_<slug>` schema, created by `metadata.create_all`
  during provisioning and versioned per-schema by Alembic (head `b2d3f5061728`).
- The column definitions below are **dialect-agnostic** (SQLAlchemy ORM). On
  PostgreSQL, `INTEGER PK` is `SERIAL`, `DATETIME` is `TIMESTAMP`, and `ENUM`
  values are enforced via the ORM / check constraints.

### Master table — `schools`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(200) | NOT NULL |
| slug | VARCHAR(50) | NOT NULL, UNIQUE, INDEX |
| db_url | VARCHAR(500) | NOT NULL — **stores the schema name** (e.g. `school_demo`) |
| address / phone / email / logo_url | — | nullable metadata |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| academic_year_start_month | INTEGER | DEFAULT 6 |
| created_at / updated_at | TIMESTAMP | NOT NULL |

### Master table — `super_admins`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| email | VARCHAR(255) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL (bcrypt) |
| first_name / last_name | VARCHAR | nullable |
| is_active | BOOLEAN | DEFAULT true |

### Master table — `super_admin_revoked_tokens`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| jti | VARCHAR(36) | NOT NULL, UNIQUE, INDEX |
| revoked_at | TIMESTAMP | NOT NULL |

---

## Entity Relationship Diagram (school-scoped tables)

> The diagram and column tables below describe the tables inside **each**
> `school_<slug>` schema. There are no `school_id` columns — isolation is at the
> schema level.

```
users ──────────────────────────────────────────────────────────────┐
  │                                                                  │
  ├──< students (user_id FK)                                         │
  │       │                                                          │
  │       ├──< student_sections (student_id FK) >── sections         │
  │       │       └── academic_year                                  │
  │       │                                                          │
  │       ├──< attendance (student_id FK) >── sections               │
  │       │                                                          │
  │       ├──< exam_results (student_id FK) >── exams >── subjects   │
  │       │                                                          │
  │       ├──< fee_records (student_id FK) >── fee_structures        │
  │       │       └──< fee_payments                                  │
  │       │                                                          │
  │       ├──< leave_applications (student_id FK) >── parents        │
  │       │                                                          │
  │       ├──< student_parent (M:M) >── parents                      │
  │       │                                                          │
  │       ├──< book_issues >── library_books                         │
  │       │                                                          │
  │       └──< student_transport >── transport_routes                │
  │                                                                  │
  ├──< teachers (user_id FK)                                         │
  │       ├──< teacher_subjects (M:M) >── subjects                   │
  │       └──< timetables >── sections >── classes                   │
  │                                                                  │
  ├──< parents (user_id FK)                                          │
  │       ├──< student_parent (M:M) >── students                     │
  │       ├──< leave_applications (parent_id FK)                     │
  │       └──< message_threads >── parent_messages                   │
  │                                                                  │
  └──< notifications (user_id FK)                                    │
                                                                     │
revoked_tokens (jti, user_id FK) ───────────────────────────────────┘
```

---

## Tables — Complete Column Definitions

### `users`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, autoincrement |
| email | VARCHAR(255) | NOT NULL, UNIQUE, INDEX |
| password_hash | VARCHAR(255) | NOT NULL |
| role | ENUM('admin','teacher','student','parent') | NOT NULL |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| created_at | DATETIME | NOT NULL, DEFAULT now |
| updated_at | DATETIME | NOT NULL, DEFAULT now |

---

### `students`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| user_id | INTEGER | FK→users.id, NOT NULL |
| admission_no | VARCHAR(20) | UNIQUE, NOT NULL, INDEX |
| first_name | VARCHAR(100) | NOT NULL |
| last_name | VARCHAR(100) | NOT NULL |
| date_of_birth | DATE | NOT NULL |
| gender | ENUM('Male','Female','Other') | NOT NULL |
| admission_date | DATE | NOT NULL |
| blood_group | VARCHAR(5) | nullable |
| address | TEXT | nullable |
| phone | VARCHAR(20) | nullable |
| photo_url | VARCHAR(500) | nullable |
| status | ENUM('active','alumni','transferred','expelled') | DEFAULT 'active' |
| leaving_date | DATE | nullable |
| is_active | BOOLEAN | DEFAULT true |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

---

### `teachers`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| user_id | INTEGER | FK→users.id, NOT NULL |
| employee_id | VARCHAR(20) | UNIQUE, NOT NULL, INDEX |
| first_name | VARCHAR(100) | NOT NULL |
| last_name | VARCHAR(100) | NOT NULL |
| date_of_birth | DATE | NOT NULL |
| gender | ENUM('Male','Female','Other') | NOT NULL |
| qualification | VARCHAR(200) | NOT NULL |
| specialization | VARCHAR(200) | nullable |
| joining_date | DATE | NOT NULL |
| phone | VARCHAR(20) | nullable |
| address | TEXT | nullable |
| photo_url | VARCHAR(500) | nullable |
| is_class_teacher | BOOLEAN | DEFAULT false |
| class_teacher_section_id | INTEGER | FK→sections.id, nullable |
| is_active | BOOLEAN | DEFAULT true |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

---

### `parents`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| user_id | INTEGER | FK→users.id, NOT NULL, UNIQUE |
| first_name | VARCHAR(100) | NOT NULL |
| last_name | VARCHAR(100) | NOT NULL |
| relationship_type | ENUM('Father','Mother','Guardian') | NOT NULL |
| phone_primary | VARCHAR(20) | NOT NULL |
| phone_secondary | VARCHAR(20) | nullable |
| occupation | VARCHAR(100) | nullable |
| address | TEXT | nullable |
| photo_url | VARCHAR(500) | nullable |
| is_active | BOOLEAN | DEFAULT true |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

---

### `student_parent` (Association)
| Column | Type | Constraints |
|--------|------|-------------|
| student_id | INTEGER | PK, FK→students.id |
| parent_id | INTEGER | PK, FK→parents.id |
| is_primary_contact | BOOLEAN | DEFAULT false |
| created_at | DATETIME | DEFAULT now |

---

### `classes`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(50) | NOT NULL (e.g. "Grade 5") |
| grade_level | INTEGER | NOT NULL, INDEX |
| description | TEXT | nullable |
| academic_year_id | INTEGER | FK→academic_years.id |
| is_active | BOOLEAN | DEFAULT true |

### `academic_years`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(20) | NOT NULL (e.g. "2024-25") |
| start_date | DATE | NOT NULL |
| end_date | DATE | NOT NULL |
| is_current | BOOLEAN | DEFAULT false |

### `sections`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| class_id | INTEGER | FK→classes.id, NOT NULL, INDEX |
| name | VARCHAR(10) | NOT NULL (e.g. "A", "B") |
| capacity | INTEGER | DEFAULT 40 |
| class_teacher_id | INTEGER | FK→teachers.id, nullable |
| is_active | BOOLEAN | DEFAULT true |

### `student_sections`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| student_id | INTEGER | FK→students.id, NOT NULL, INDEX |
| section_id | INTEGER | FK→sections.id, NOT NULL, INDEX |
| academic_year_id | INTEGER | FK→academic_years.id |
| start_date | DATE | NOT NULL |
| end_date | DATE | nullable |
| is_current | BOOLEAN | DEFAULT true, INDEX |
| transfer_reason | TEXT | nullable |

---

### `subjects`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(100) | NOT NULL |
| code | VARCHAR(20) | UNIQUE, NOT NULL |
| description | TEXT | nullable |
| max_marks | INTEGER | NOT NULL, DEFAULT 100 |
| pass_marks | INTEGER | NOT NULL, DEFAULT 40 |
| is_active | BOOLEAN | DEFAULT true |

### `teacher_subjects` (Association)
| Column | Type | Constraints |
|--------|------|-------------|
| teacher_id | INTEGER | PK, FK→teachers.id |
| subject_id | INTEGER | PK, FK→subjects.id |
| academic_year_id | INTEGER | FK→academic_years.id |

### `timetables`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| section_id | INTEGER | FK→sections.id, NOT NULL, INDEX |
| subject_id | INTEGER | FK→subjects.id, NOT NULL |
| teacher_id | INTEGER | FK→teachers.id, NOT NULL |
| day_of_week | INTEGER | NOT NULL (1=Mon…6=Sat) |
| period_no | INTEGER | NOT NULL |
| start_time | TIME | NOT NULL |
| end_time | TIME | NOT NULL |

**Unique constraint:** `(section_id, day_of_week, period_no)` — no two subjects in same slot
**Unique constraint:** `(teacher_id, day_of_week, period_no)` — no teacher double-booked

---

### `attendance`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| student_id | INTEGER | FK→students.id, NOT NULL, INDEX |
| section_id | INTEGER | FK→sections.id, NOT NULL, INDEX |
| date | DATE | NOT NULL, INDEX |
| status | ENUM('present','absent','late','leave','holiday') | NOT NULL |
| marked_by | INTEGER | FK→users.id |
| remarks | TEXT | nullable |
| created_at | DATETIME | NOT NULL |

**Unique constraint:** `(student_id, section_id, date)` — one record per student per day

---

### `exams`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(100) | NOT NULL |
| term | VARCHAR(50) | NOT NULL (e.g. "Term 1") |
| exam_type | ENUM('unit','midterm','final','practical') | NOT NULL |
| section_id | INTEGER | FK→sections.id, NOT NULL, INDEX |
| academic_year_id | INTEGER | FK→academic_years.id |
| conducted_date | DATE | NOT NULL |
| is_active | BOOLEAN | DEFAULT true |

### `exam_results`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| exam_id | INTEGER | FK→exams.id, NOT NULL, INDEX |
| student_id | INTEGER | FK→students.id, NOT NULL, INDEX |
| subject_id | INTEGER | FK→subjects.id, NOT NULL |
| marks_obtained | NUMERIC(5,2) | NOT NULL |
| grade | VARCHAR(3) | NOT NULL |
| gpa | NUMERIC(3,2) | NOT NULL |
| status | ENUM('draft','finalized') | DEFAULT 'draft' |
| created_by | INTEGER | FK→users.id |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

**Unique constraint:** `(exam_id, student_id, subject_id)`

---

### `fee_structures`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| class_id | INTEGER | FK→classes.id, nullable (null=school-wide) |
| fee_type | VARCHAR(100) | NOT NULL (e.g. "Tuition","Library","Transport") |
| amount | NUMERIC(10,2) | NOT NULL |
| due_day | INTEGER | NOT NULL (day of month, e.g. 15) |
| academic_year_id | INTEGER | FK→academic_years.id |
| is_recurring | BOOLEAN | DEFAULT true |
| frequency | ENUM('monthly','quarterly','annual','one_time') | NOT NULL |
| is_active | BOOLEAN | DEFAULT true |

### `fee_records`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| student_id | INTEGER | FK→students.id, NOT NULL, INDEX |
| fee_structure_id | INTEGER | FK→fee_structures.id |
| amount | NUMERIC(10,2) | NOT NULL |
| discount | NUMERIC(10,2) | DEFAULT 0.00 |
| net_amount | NUMERIC(10,2) | NOT NULL (amount - discount) |
| due_date | DATE | NOT NULL, INDEX |
| status | ENUM('pending','paid','partial','overdue','waived') | DEFAULT 'pending', INDEX |
| remarks | TEXT | nullable |
| created_at | DATETIME | NOT NULL |

### `fee_payments`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| fee_record_id | INTEGER | FK→fee_records.id, NOT NULL, INDEX |
| amount_paid | NUMERIC(10,2) | NOT NULL |
| payment_method | ENUM('cash','bank_transfer','cheque','online','dd') | NOT NULL |
| payment_date | DATE | NOT NULL |
| receipt_no | VARCHAR(30) | UNIQUE, NOT NULL |
| transaction_reference | VARCHAR(100) | nullable |
| collected_by | INTEGER | FK→users.id |
| remarks | TEXT | nullable |
| created_at | DATETIME | NOT NULL |

---

### `leave_applications`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| student_id | INTEGER | FK→students.id, NOT NULL, INDEX |
| parent_id | INTEGER | FK→parents.id, NOT NULL, INDEX |
| from_date | DATE | NOT NULL |
| to_date | DATE | NOT NULL |
| reason | TEXT | NOT NULL |
| leave_type | ENUM('sick','family','personal','other') | DEFAULT 'personal' |
| status | ENUM('pending','approved','rejected') | DEFAULT 'pending', INDEX |
| reviewed_by | INTEGER | FK→users.id, nullable |
| reviewed_at | DATETIME | nullable |
| reviewer_remarks | TEXT | nullable |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

---

### `notifications`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| user_id | INTEGER | FK→users.id, NOT NULL, INDEX |
| type | ENUM('absence','low_marks','fee_due','message','announcement','leave_update') | NOT NULL |
| title | VARCHAR(200) | NOT NULL |
| body | TEXT | NOT NULL |
| reference_id | INTEGER | nullable |
| reference_type | VARCHAR(50) | nullable |
| is_read | BOOLEAN | DEFAULT false, INDEX |
| created_at | DATETIME | NOT NULL, INDEX |

---

### `message_threads`
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PK (UUID) |
| parent_id | INTEGER | FK→parents.id, NOT NULL, INDEX |
| teacher_id | INTEGER | FK→teachers.id, NOT NULL, INDEX |
| student_id | INTEGER | FK→students.id, NOT NULL |
| subject | VARCHAR(255) | NOT NULL |
| created_at | DATETIME | NOT NULL |
| last_message_at | DATETIME | NOT NULL, INDEX |

### `parent_messages`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| thread_id | VARCHAR(36) | FK→message_threads.id, NOT NULL, INDEX |
| sender_id | INTEGER | FK→users.id, NOT NULL |
| body | TEXT | NOT NULL |
| is_read | BOOLEAN | DEFAULT false |
| created_at | DATETIME | NOT NULL |

---

### `announcements`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| title | VARCHAR(255) | NOT NULL |
| content | TEXT | NOT NULL |
| target_roles | JSON | nullable (null = all roles) |
| target_class_ids | JSON | nullable (null = all classes) |
| status | ENUM('draft','published','archived') | DEFAULT 'draft', INDEX |
| published_at | DATETIME | nullable |
| expires_at | DATETIME | nullable |
| created_by | INTEGER | FK→users.id |
| created_at | DATETIME | NOT NULL |

---

### `library_books`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| isbn | VARCHAR(20) | UNIQUE, nullable |
| title | VARCHAR(255) | NOT NULL, INDEX |
| author | VARCHAR(255) | NOT NULL |
| publisher | VARCHAR(255) | nullable |
| category | VARCHAR(100) | nullable, INDEX |
| total_copies | INTEGER | NOT NULL, DEFAULT 1 |
| available_copies | INTEGER | NOT NULL, DEFAULT 1 |
| is_active | BOOLEAN | DEFAULT true |

### `book_issues`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| book_id | INTEGER | FK→library_books.id, NOT NULL |
| student_id | INTEGER | FK→students.id, NOT NULL, INDEX |
| issued_date | DATE | NOT NULL |
| due_date | DATE | NOT NULL |
| returned_date | DATE | nullable |
| fine_amount | NUMERIC(8,2) | DEFAULT 0.00 |
| status | ENUM('issued','returned','lost') | DEFAULT 'issued', INDEX |

---

### `transport_routes`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(100) | NOT NULL |
| description | TEXT | nullable |
| stops_json | JSON | NOT NULL (list of stop names) |
| is_active | BOOLEAN | DEFAULT true |

### `transport_vehicles`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| registration_no | VARCHAR(20) | UNIQUE, NOT NULL |
| capacity | INTEGER | NOT NULL |
| driver_name | VARCHAR(100) | NOT NULL |
| driver_phone | VARCHAR(20) | NOT NULL |
| route_id | INTEGER | FK→transport_routes.id |
| is_active | BOOLEAN | DEFAULT true |

### `student_transport`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| student_id | INTEGER | FK→students.id, NOT NULL |
| route_id | INTEGER | FK→transport_routes.id, NOT NULL |
| pickup_stop | VARCHAR(100) | NOT NULL |
| drop_stop | VARCHAR(100) | NOT NULL |
| academic_year_id | INTEGER | FK→academic_years.id |
| is_active | BOOLEAN | DEFAULT true |

---

### `revoked_tokens`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| jti | VARCHAR(36) | UNIQUE, NOT NULL, INDEX |
| user_id | INTEGER | FK→users.id |
| revoked_at | DATETIME | NOT NULL |
| expires_at | DATETIME | NOT NULL |

### `password_reset_tokens`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| user_id | INTEGER | FK→users.id, NOT NULL |
| token_hash | VARCHAR(64) | NOT NULL, INDEX |
| expires_at | DATETIME | NOT NULL |
| used_at | DATETIME | nullable |
| created_at | DATETIME | NOT NULL |

### `student_documents`
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK |
| student_id | INTEGER | FK→students.id, NOT NULL, INDEX |
| document_type | ENUM('birth_certificate','transfer_certificate','photo','medical','other') | NOT NULL |
| file_name | VARCHAR(255) | NOT NULL |
| file_path | VARCHAR(500) | NOT NULL |
| uploaded_by | INTEGER | FK→users.id |
| created_at | DATETIME | NOT NULL |

---

## Index Strategy

```sql
-- High-frequency lookup indexes (beyond PKs and declared above)
CREATE INDEX idx_attendance_date       ON attendance(date);
CREATE INDEX idx_attendance_student    ON attendance(student_id, date);
CREATE INDEX idx_exam_results_student  ON exam_results(student_id, exam_id);
CREATE INDEX idx_fee_records_status    ON fee_records(status, due_date);
CREATE INDEX idx_notifications_unread  ON notifications(user_id, is_read, created_at);
CREATE INDEX idx_student_sections_cur  ON student_sections(student_id, is_current);
```
