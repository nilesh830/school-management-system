# SMS — End-to-End Demo Guide

> **Purpose:** A complete, ordered script to (1) set up a school with full data so you can rehearse, and (2) present every screen and portal to a client confidently.
>
> **Tip (Hindi):** Pehle is guide ko follow karke ek school poora bana lo aur har screen khud try kar lo. Jab confident ho jao, tab client ke saamne wahi order repeat karo. Har step ke saath "Kya bolna hai" (talking point) diya hai.

---

## How the system is structured (mental model)

This is a **multi-tenant ERP**: one Super Admin manages many schools; each school has its own isolated database and its own users.

| Portal | URL | Who logs in | Login needs |
|--------|-----|-------------|-------------|
| **Super Admin** | `/superadmin/login` | Platform owner (you) | email + password (no school slug) |
| **School Admin** | `/login` → `/admin` | School administrator | email + password + **school slug** |
| **Teacher** | `/login` → `/teacher` | Teachers | email + password + school slug |
| **Parent** | `/login` → `/parent` | Parents / guardians | email + password + school slug |
| **Student** | `/login` → `/student` | Students | email + password + school slug |

> **Key point for the client:** every school's data is fully isolated, and a parent can only ever see their own children. This is enforced server-side.

---

## PART 0 — One-time setup (do this before the demo)

### 0.1 Start the servers

**Backend** (terminal 1):
```bash
cd backend
venv\Scripts\activate           # Windows; on first run: pip install -r requirements.txt
python run.py                   # serves http://localhost:5000
```

**Frontend** (terminal 2):
```bash
cd frontend
npm install                     # first run only
npm start                       # serves http://localhost:4200 (proxies /api to :5000)
```

Open **http://localhost:4200** in the browser.

### 0.2 Seed the Super Admin (one time)

```bash
cd backend
python database/seeds/seed_master.py
```

This creates the platform Super Admin:

| Field | Value |
|-------|-------|
| Super Admin email | `superadmin@sms.com` |
| Super Admin password | `SuperAdmin@1234` |

### 0.3 Recommended: create a FRESH school for the demo

There is an old "Demo School" (slug `demo`) in the system, but its data is incomplete and it predates the Transport module. **For a clean, complete demo, provision a brand-new school** (steps in Part 1.A) — you choose its admin email/password, and its schema includes every module.

### 0.4 Create the Academic Year (IMPORTANT — no UI for this)

Fee Structures and Transport Assignments need an Academic Year, but there is **no admin screen** to create one. After you provision your school (slug e.g. `sunrise`), run once:

```bash
cd backend
python database/seeds/seed_academic_year.py sunrise
```

This creates academic year **2025-2026** for that school. (Without it, the Fees and Transport screens will have an empty year dropdown.)

---

## PART 1 — The recommended demo flow (the story to tell)

Present in this order — it tells a natural story: *spin up a school → set up academics → add people → run daily operations → communicate → show what parents/students/teachers see → prove it with reports.*

```
A. Super Admin     → create the school
B. School Admin    → Academics (classes, subjects, sections, timetable)
                   → People (teachers, students, parents, enrollment, links)
                   → Daily ops (attendance, exams & marks, fees)
                   → Services (announcements, library, transport)
C. Teacher portal  → mark attendance, enter marks, view timetable
D. Parent portal   → children, attendance/grades/fees, leave, messages, notices
E. Student portal  → own attendance & grades
F. Admin reports   → dashboard KPIs + attendance/grades/fees reports + PDF/Excel export
```

---

## PART 2 — Step-by-step by portal & screen

> Legend: **➡️ Do** = what to click/enter. **🗣️ Say** = the talking point for the client.

---

### A. SUPER ADMIN PORTAL — create the school

Go to **`/superadmin/login`**.

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| A1 | **SA Login** | Log in with `superadmin@sms.com` / `SuperAdmin@1234` | "This is the platform owner's control panel that manages all schools." |
| A2 | **SA Dashboard** | Show the school cards + counts | "At a glance — every school on the platform and its status." |
| A3 | **Schools list** (`/superadmin/schools`) | Show the searchable, paginated table | "Search and manage any school." |
| A4 | **Provision new school** (`/superadmin/schools/new`) | Fill the form (see fields below) and submit | "Onboarding a new school takes seconds — and it gets its own isolated database." |
| A5 | **School detail** (`/superadmin/schools/:id`) | Show detail; demo activate/deactivate | "We can suspend or reactivate a school instantly." |

**Provision form fields:**

| Field | Example | Notes |
|-------|---------|-------|
| Name | `Sunrise Public School` | required |
| Slug | `sunrise` | required, lowercase/hyphens; **this is the login slug** |
| Admin email | `admin@sunrise.sms` | required — first admin login |
| Admin password | `Admin@1234` | required, min 8 chars |
| Admin first/last name | `Sunita` / `Rao` | optional |
| Address / Phone / Email | (any) | optional |

> After provisioning, **run `seed_academic_year.py sunrise`** (Part 0.4).

---

### B. SCHOOL ADMIN PORTAL

Go to **`/login`** → enter the admin email/password **and the slug `sunrise`** → lands on `/admin`.

#### B0. Admin Dashboard (`/admin/dashboard`)
- 🗣️ "This is the principal's command center." Early on it's mostly empty — **come back to it at the end** (Part F) once data exists, to show live KPIs and charts.

#### B1. Academics setup (do in this order)

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| B1.1 | **Classes** (`/admin/classes`) | Add classes e.g. *Grade 1*, *Grade 2* (name + grade level) | "We define the school's grades." |
| B1.2 | **Subjects** (`/admin/subjects`) | Add subjects e.g. *Mathematics*, *English*, *Science* (set **max marks**, e.g. 100) | "Subjects carry their max marks — used later for grading." |
| B1.3 | **Class detail → Sections** (`/admin/classes/:id`) | Open a class, add a **Section** e.g. *A* (assign a class teacher later) | "Each class splits into sections." |
| B1.4 | **Timetable** (`/admin/timetable`) | Create a few periods (day, time, subject, section) | "Weekly timetable per section." |

#### B2. People

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| B2.1 | **Teachers → New** (`/admin/teachers/new`) | Add 2 teachers (name, email, password, etc.) | "Add faculty — each gets a login." |
| B2.2 | **Teacher detail** (`/admin/teachers/:id`) | Assign subjects to the teacher; view schedule | "Assign what each teacher teaches." |
| B2.3 | **Students → New** (`/admin/students/new`) | Add 3–4 students (admission no, name, DOB, gender, admission date) | "Enroll students with full profiles." |
| B2.4 | **Class detail → Enroll** (`/admin/classes/:id`) | Enroll the students into Section A | "Place students into sections." |
| B2.5 | **Create User** (`/admin/users/new`) | Create **parent** users (role = Parent/Guardian) | "Parents get their own logins." |
| B2.6 | **Student detail → Parents** (`/admin/students/:id`) | Link each parent to their child (mark primary contact) | "Link guardians to students — this drives the Parent Portal isolation." |

> Note the credentials you set for one teacher, one parent, and one student — you'll log in as them in Parts C–E.

#### B3. Daily operations

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| B3.1 | **Attendance** (`/admin/attendance` or via Teacher portal) | Mark today's attendance for Section A (toggle present/absent) | "One-tap daily attendance; absences notify parents." |
| B3.2 | **Exams** (`/admin/exams`) | Create an exam (name, class, date) | "Define exams per class." |
| B3.3 | **Marks entry** (`/admin/exams/:id/marks`) | Enter subject marks for each student | "Subject-wise marks with auto-grade calculation." |
| B3.4 | **Class results** (`/admin/exams/:id/results`) | Show the result summary + grade-distribution chart | "Instant class performance view." |
| B3.5 | **Finalize exam** (on marks-entry, admin only) | Click *Finalize* | "Locks marks from further edits — approval workflow." |
| B3.6 | **Report card** (Student detail → Report Cards tab) | Download the PDF | "Printable report card per student." |
| B3.7 | **Fees** (`/admin/fees`) | Create a fee structure (class, **academic year**, type, amount) | "Fee structures per class/year." |
| B3.8 | **Generate records** (Fees → Generate on a structure) | Generate fee records for the class | "One click bills every student in the class." |
| B3.9 | **Fee payment** (`/admin/fees/payment`) | Search a student, record a payment | "Record payments; receipt number auto-generated." |
| B3.10 | **Fee ledger** (`/admin/fees/ledger`) | Show payment history; **Download Receipt** PDF | "Full ledger + printable receipts." |
| B3.11 | **Fee defaulters** (`/admin/fees/defaulters`) | Show overdue list, export CSV | "Instantly see who hasn't paid." |
| B3.12 | **Discount** (Fee payment → apply discount) | Apply a scholarship/discount to a record | "Scholarships and concessions are handled." |

#### B4. Services

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| B4.1 | **Announcements** (`/admin/announcements`) | Create a notice, target *Parents*, then **Publish** | "School-wide or targeted notices — published instantly to parents." |
| B4.2 | **Library** (`/admin/library`) | Add a book (title, author, copies) | "Library catalog with copy tracking." |
| B4.3 | **Library issues** (`/admin/library/issues`) | Issue a book to a student, then return it (show fine if overdue) | "Issue/return with automatic overdue fines." |
| B4.4 | **Transport** (`/admin/transport`) | **Routes** tab: add a route (name + stops). **Vehicles** tab: add a vehicle (reg no, capacity, driver, route). **Assignments** tab: assign a student (route + academic year + stops) | "Manage routes, buses, and student transport assignments." |
| B4.5 | **Leave Requests** (`/admin/leave-requests`) | (After a parent submits one in Part D) approve/reject it | "Review leave requests; approval auto-marks attendance." |

---

### C. TEACHER PORTAL

Log out, go to **`/login`**, log in as the **teacher** (email/password + slug `sunrise`) → `/teacher`.

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| C1 | **Teacher Dashboard** (`/teacher/dashboard`) | Show overview | "The teacher's home." |
| C2 | **Mark Attendance** (`/teacher/attendance/mark`) | Pick section + date, toggle attendance, save | "Teachers mark their own section — they can't touch others." |
| C3 | **Attendance View / Report** (`/teacher/attendance/view`, `/report`) | Show calendar + report | "Teachers track attendance trends." |
| C4 | **Timetable** (`/teacher/timetable`) | Show the teacher's schedule | "Each teacher sees their own timetable." |
| C5 | **Profile** (`/teacher/profile`) | Show profile | — |

> 🗣️ **Role restriction proof:** a teacher has no Fees/Users/Transport menu — they only see what their role allows.

---

### D. PARENT PORTAL (the highlight — mobile-first)

Log out, log in as a **parent** (+ slug `sunrise`) → `/parent`.

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| D1 | **Parent Dashboard** (`/parent/dashboard`) | Show child summary cards (attendance %, grade, fees) | "Parents see all their children at a glance." |
| D2 | **Child Attendance** (`/parent/children/:id/attendance`) | Open the color-coded calendar, navigate months | "Day-by-day attendance for their child." |
| D3 | **Child Grades** (`/parent/children/:id/grades`) | Expand an exam, view subjects, download report card PDF | "Exam results and report cards." |
| D4 | **Child Fees** (`/parent/children/:id/fees`) | Show fee status, outstanding banner, download receipt | "Fee status and receipts — full transparency." |
| D5 | **Leave Applications** (`/parent/leave-applications`) | **Submit a leave** (child, date range, reason) | "Parents request leave online." → now go approve it in **B4.5**. |
| D6 | **Messages** (`/parent/messages`) | Start a thread to the class teacher; send a message | "Direct parent-teacher messaging." |
| D7 | **Notices** (`/parent/notices`) | Show the announcement you published in B4.1 | "School notices reach parents here." |
| D8 | **Notification bell** (top bar) | Show unread badge + dropdown | "Real-time alerts for absences, grades, replies." |
| D9 | **Profile** (`/parent/profile`) | Edit profile (email is locked) | "Parents manage their own details." |

> 🗣️ **Isolation proof:** "This parent sees only their own child — there's no way to view another family's data."

---

### E. STUDENT PORTAL

Log out, log in as a **student** (+ slug `sunrise`) → `/student`.

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| E1 | **Student Dashboard** (`/student/dashboard`) | Show overview | "The student's home view." |
| E2 | **Attendance** (`/student/attendance`) | Show own attendance calendar | "Students track their own attendance." |
| E3 | **Profile** (`/student/profile`) | Show profile | "Students can only ever see their own data." |

---

### F. ADMIN REPORTS & DASHBOARD (the closer)

Log back in as **admin**. Now that data exists, this is the impressive finish.

| # | Screen | ➡️ Do | 🗣️ Say |
|---|--------|-------|--------|
| F1 | **Admin Dashboard** (`/admin/dashboard`) | Show the 4 KPI cards, fee-collection & attendance doughnuts, alerts panel | "Live KPIs across the whole school — students, attendance, fees, pending actions." |
| F2 | **Attendance Report** (`/admin/reports/attendance`) | Filter by section + dates; show table + chart; **Export PDF / Excel** | "Analytics with one-click export." |
| F3 | **Grades Report** (`/admin/reports/grades`) | Pick exam; show distribution; export | "Academic performance analytics." |
| F4 | **Fees Report** (`/admin/reports/fees`) | Show collection summary + defaulters; export | "Financial reporting with exports for accounts." |

> 🗣️ **Close with:** "Everything you saw — academics, attendance, exams, fees, communication, transport, and parent engagement — is one integrated, secure, multi-school platform."

---

## PART 3 — Pre-demo checklist (so no screen is empty)

Before the client arrives, make sure you've created at least:

- [ ] 1 fresh school provisioned (slug noted) + `seed_academic_year.py <slug>` run
- [ ] 2 classes, 3 subjects (with max marks), 1–2 sections
- [ ] 2 teachers (+ subject assignments), 3–4 students (enrolled in a section)
- [ ] 2 parents, each linked to a child (note their logins)
- [ ] Attendance marked for at least 1 day
- [ ] 1 exam created + marks entered + finalized (so report cards/grades show)
- [ ] 1 fee structure + records generated + 1 payment recorded
- [ ] 1 published announcement, 1 library book, 1 transport route + vehicle + 1 assignment
- [ ] 1 leave application submitted (as parent) — leave it pending to approve live, or approve it
- [ ] Logins handy for: admin, one teacher, one parent, one student (all use slug)

---

## PART 4 — Demo-day tips

- **Keep 4 browser tabs / profiles** open (admin, teacher, parent, student) so you can switch roles without re-logging-in each time. Use separate browser profiles or incognito windows (tokens are per-session).
- **Always type the school slug** at `/login` — forgetting it is the #1 demo mistake.
- Lead with the **Parent Portal** and **Dashboard/Reports** — they're the most visually impressive.
- Emphasize **data isolation** and **role-based access** — big selling points for schools.
- If asked about deployment/scale: "It's built multi-tenant from day one; each school is isolated, and it's ready for cloud deployment."

---

## PART 5 — Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| Login fails with valid email/password | Missing or wrong **school slug**. Use the exact slug (e.g. `sunrise`). |
| Fees / Transport "academic year" dropdown is empty | Run `python database/seeds/seed_academic_year.py <slug>` (Part 0.4). |
| Transport screen errors on an old school | The old `demo`/`greenwood-high` DBs predate the Transport module. **Use a freshly provisioned school** — its schema includes all modules. |
| Frontend can't reach API | Backend not running on `:5000`, or you didn't use `npm start` (it carries the proxy). Restart both. |
| Super Admin login won't accept a slug | Correct — Super Admin logs in at `/superadmin/login` with **no** slug. |
| Parent dashboard is empty | The parent isn't linked to any student. Link them in **Student detail → Parents** (B2.6). |
| Report card / report shows no data | Marks not entered/finalized, or attendance not marked yet. |

---

## Quick credential reference

| Role | Where | Login |
|------|-------|-------|
| Super Admin | `/superadmin/login` | `superadmin@sms.com` / `SuperAdmin@1234` (no slug) |
| School Admin | `/login` | the admin email/password you set when provisioning + **slug** |
| Teacher / Parent / Student | `/login` | the credentials you set in the admin panel + **slug** |

> The older **Demo School** (slug `demo`, admin `admin@school.sms`) exists but is incomplete and pre-Transport — prefer a fresh school for demos.
