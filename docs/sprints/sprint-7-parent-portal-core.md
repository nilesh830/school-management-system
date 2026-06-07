# Sprint 7 — Parent Portal: Core (Read)
**Scrum Master:** @scrum-master | **Dates:** Week 13–14
**Sprint Goal:** Deliver the read-only Parent Portal so parents can see their child's attendance, grades, fees, and school notices — closing the visibility gap between school and home.
**Velocity Target:** 32 pts | **Epic:** EPIC-08
**Dependencies:** Sprints 1–6 complete (students, attendance, grades, fees all working)

---

## Sprint Board

| Story | Title | Points | Assignee | Status |
|-------|-------|--------|----------|--------|
| SMS-041 | Parent Dashboard (All Children Overview) | 8 | @frontend-engineer + @backend-engineer | To Do |
| SMS-042 | Child Attendance Monitor | 8 | @frontend-engineer + @backend-engineer | To Do |
| SMS-043 | Academic Performance View | 8 | @frontend-engineer + @backend-engineer | To Do |
| SMS-044 | Fee Status & History | 5 | @frontend-engineer + @backend-engineer | To Do |
| SMS-045 | School Notice Board (Parent View) | 3 | @frontend-engineer | To Do |

---

## Stories — Full Detail

---

### SMS-041: Parent Dashboard (All Children Overview)
**Epic:** EPIC-08 | **Points:** 8 | **Priority:** Must

**User Story:**
> As a parent,
> I want to see an at-a-glance overview of all my children's key stats when I log in,
> So that I instantly know if any child needs my attention without navigating multiple pages.

**Acceptance Criteria:**
- [ ] Given I am a parent, When I navigate to `/parent/dashboard`, Then I see a card for each linked child
- [ ] Each child card shows: name, class/section, attendance % (current month), outstanding fee amount, and latest exam grade
- [ ] Given I have 3 children, Then all 3 cards are visible (scrollable on mobile)
- [ ] Given I click a child card, Then I navigate to that child's detailed view
- [ ] Given I am a parent with NO linked children, Then I see a message: "No children linked. Contact your school admin."
- [ ] Given unread notifications > 0, Then a badge shows in the header (e.g. 🔔 3)
- [ ] Mobile: all cards are full-width stacked on 375px viewport

**Dependencies:** SMS-010 (parent linking), SMS-024 (attendance), SMS-030 (grades), SMS-037 (fees)

---

#### Tech Specification — SMS-041

**Backend API:**
```
GET /api/v1/parent-portal/dashboard
Role Required: parent
JWT: parent_id extracted from token claims

Response 200: {
  "data": {
    "parent": { "id": 1, "first_name": "John", "last_name": "Doe" },
    "children": [
      {
        "student": { "id": 5, "first_name": "Alice", "admission_no": "ADM2024001", "class": "Grade 5 - A" },
        "attendance_summary": { "month": 6, "year": 2026, "present": 18, "absent": 2, "percentage": 90.0 },
        "pending_fees": { "total_due": 5000.00, "overdue_count": 1 },
        "recent_grades": { "exam": "Midterm 2026", "average_marks": 82.5, "grade": "A" }
      }
    ],
    "unread_notifications": 3
  }
}
```

**Data Isolation Rule:** `ParentPortalService.get_dashboard(parent_id)` queries `student_parent` table filtered by `parent_id` from JWT. No other parent's data is ever loaded.

**Frontend Components:**
```
modules/parent-portal/
├── layout/
│   ├── parent-layout.component.ts    # Wrapper with sidebar + header
│   ├── parent-sidebar.component.ts   # Mobile-collapsible sidebar
│   └── parent-header.component.ts    # Child switcher + notification bell
├── dashboard/
│   ├── dashboard.component.ts
│   ├── dashboard.component.html
│   └── child-summary-card.component.ts   # Reusable card per child
```

**Child Summary Card — PrimeNG Layout:**
```html
<p-card styleClass="child-card mb-3">
  <ng-template pTemplate="header">
    <div class="flex align-items-center gap-2 p-3">
      <p-avatar [image]="child.student.photo_url" size="large" shape="circle"/>
      <div>
        <h3 class="m-0">{{ child.student.first_name }} {{ child.student.last_name }}</h3>
        <small class="text-500">{{ child.student.class }}</small>
      </div>
    </div>
  </ng-template>
  <div class="grid">
    <div class="col-4 text-center">
      <p-knob [ngModel]="child.attendance_summary.percentage" [readonly]="true"
              [valueColor]="getAttendanceColor(child.attendance_summary.percentage)"/>
      <small>Attendance</small>
    </div>
    <div class="col-4 text-center">
      <span class="text-2xl font-bold text-red-500">₹{{ child.pending_fees.total_due }}</span>
      <br><small>Fees Due</small>
    </div>
    <div class="col-4 text-center">
      <p-badge [value]="child.recent_grades.grade" severity="success"/>
      <br><small>Last Exam</small>
    </div>
  </div>
</p-card>
```

**Color logic:** attendance ≥85% → green, 70–84% → orange, <70% → red

---

#### Tasks — SMS-041

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-041-01 | Implement `GET /api/v1/parent-portal/dashboard` with real attendance/fee/grade data | BE | @backend-engineer | 3h |
| T-041-02 | Implement `ParentPortalService.get_dashboard()` aggregating all child data | BE | @backend-engineer | 2h |
| T-041-03 | Create `parent-portal.module.ts` with lazy-loaded routing | FE | @frontend-engineer | 1h |
| T-041-04 | Build parent layout shell (sidebar + header + notification bell) | FE | @frontend-engineer | 3h |
| T-041-05 | Build `dashboard.component` with child summary cards | FE | @frontend-engineer | 3h |
| T-041-06 | Build reusable `child-summary-card` component with PrimeNG Knob | FE | @frontend-engineer | 2h |
| T-041-07 | Implement mobile-responsive layout (375px breakpoint) | FE | @frontend-engineer | 1h |
| T-041-08 | Test: 1 child, 3 children, 0 children, data isolation (parent can't see other's child) | QA | @qa-engineer | 2h |
| T-041-09 | Security: verify parent_id in JWT matches student_parent link, no enumeration | SEC | @security-engineer | 1h |

---

### SMS-042: Child Attendance Monitor
**Epic:** EPIC-08 | **Points:** 8 | **Priority:** Must

**User Story:**
> As a parent,
> I want to see my child's daily attendance on a calendar view with monthly stats,
> So that I can track their attendance habit and take action when absences accumulate.

**Acceptance Criteria:**
- [ ] Given I select a child and month, When I view attendance, Then I see a calendar with color-coded days (green=present, red=absent, yellow=late, grey=holiday)
- [ ] Given the month, Then I see a summary: X present, Y absent, Z late, Attendance %
- [ ] Given a month with no attendance records, Then I see "No attendance data for this period"
- [ ] Given I switch month (prev/next), Then data updates without page reload
- [ ] Mobile: calendar is scrollable and readable on 375px

**Dependencies:** SMS-024 (attendance marking must be done by teacher first), SMS-041

---

#### Tech Specification — SMS-042

**Backend API:**
```
GET /api/v1/parent-portal/children/:id/attendance?month=6&year=2026
Role Required: parent
Validates: child must be linked to requesting parent (via student_parent)

Response 200: {
  "data": {
    "student_id": 5,
    "month": 6, "year": 2026,
    "records": [
      { "date": "2026-06-01", "status": "present", "section": "Grade 5 A" },
      { "date": "2026-06-02", "status": "absent", "reason": null },
      { "date": "2026-06-03", "status": "holiday" }
    ],
    "summary": { "present": 18, "absent": 2, "late": 1, "holidays": 4, "percentage": 90.0 }
  }
}
```

**Frontend Component:**
```typescript
// attendance.component.ts
export class AttendanceComponent implements OnInit {
  selectedChild: any;
  currentMonth = new Date().getMonth() + 1;
  currentYear = new Date().getFullYear();
  attendanceMap = new Map<string, string>(); // date → status

  getStatusClass(date: Date): string {
    const key = date.toISOString().split('T')[0];
    const status = this.attendanceMap.get(key);
    return { 'present': 'bg-green-200', 'absent': 'bg-red-200',
             'late': 'bg-yellow-200', 'holiday': 'bg-gray-100' }[status] || '';
  }
}
```

**UI Pattern:** Use PrimeNG `p-calendar` in `inline` mode as a read-only display, OR build a custom month grid with colored cells (custom grid gives better mobile control).

---

#### Tasks — SMS-042

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-042-01 | Implement `GET /api/v1/parent-portal/children/:id/attendance` — query attendance by month | BE | @backend-engineer | 2h |
| T-042-02 | Compute monthly summary stats (present, absent, late, %) | BE | @backend-engineer | 1h |
| T-042-03 | Build attendance calendar grid component (color-coded cells) | FE | @frontend-engineer | 3h |
| T-042-04 | Add month prev/next navigation without page reload | FE | @frontend-engineer | 1h |
| T-042-05 | Add monthly summary stats row (present/absent/late/%) | FE | @frontend-engineer | 1h |
| T-042-06 | Child switcher dropdown in header (switch between linked children) | FE | @frontend-engineer | 1h |
| T-042-07 | Test: correct data per month, data isolation, no-data state, month navigation | QA | @qa-engineer | 2h |

---

### SMS-043: Academic Performance View
**Epic:** EPIC-08 | **Points:** 8 | **Priority:** Must

**User Story:**
> As a parent,
> I want to see my child's exam results and subject-wise marks,
> So that I can identify strong and weak subjects and support their learning at home.

**Acceptance Criteria:**
- [ ] Given I view grades, Then I see a list of all exams with: exam name, term, marks per subject, total, grade, GPA
- [ ] Given I click an exam, Then I see subject-wise breakdown with marks obtained vs max marks
- [ ] Given marks are below 40% in any subject, Then that subject is highlighted in red
- [ ] Given I click "Download Report Card", Then a PDF is generated and downloaded
- [ ] Given no exams have been entered yet, Then I see "No exam results available yet"

**Dependencies:** SMS-030 (marks entry), SMS-032 (report card generation), SMS-041

---

#### Tech Specification — SMS-043

**Backend API:**
```
GET /api/v1/parent-portal/children/:id/grades
Response 200: {
  "data": {
    "student_id": 5,
    "student_name": "Alice Johnson",
    "section": "Grade 5 - A",
    "exams": [
      {
        "exam_id": 1,
        "exam_name": "Midterm 2026",
        "term": "Term 1",
        "conducted_date": "2026-03-15",
        "subjects": [
          { "subject": "Mathematics", "marks_obtained": 82, "max_marks": 100, "grade": "A", "pass": true },
          { "subject": "Science", "marks_obtained": 35, "max_marks": 100, "grade": "F", "pass": false }
        ],
        "total_marks": 117,
        "total_max": 200,
        "percentage": 58.5,
        "gpa": 2.8,
        "overall_grade": "C"
      }
    ]
  }
}

GET /api/v1/parent-portal/children/:id/report-card/:exam_id → returns PDF
```

**Frontend Components:**
- Exam list with `p-accordion` (each exam is an accordion panel)
- Inside each panel: `p-table` with subject marks
- Failed subjects (< 40%) highlighted with `bg-red-50` row class
- Bar chart (`p-chart` type=bar) showing subject-wise performance
- "Download Report Card" button calls the PDF endpoint

---

#### Tasks — SMS-043

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-043-01 | Implement `GET /api/v1/parent-portal/children/:id/grades` | BE | @backend-engineer | 2h |
| T-043-02 | Add report card PDF download endpoint | BE | @backend-engineer | 2h |
| T-043-03 | Build grades view with `p-accordion` per exam | FE | @frontend-engineer | 2h |
| T-043-04 | Add subject-wise bar chart with `p-chart` | FE | @frontend-engineer | 1.5h |
| T-043-05 | Highlight failed subjects in red | FE | @frontend-engineer | 0.5h |
| T-043-06 | Wire PDF download button | FE | @frontend-engineer | 0.5h |
| T-043-07 | Test: multi-exam, fail highlight, PDF download, data isolation | QA | @qa-engineer | 1.5h |

---

### SMS-044: Fee Status & History
**Epic:** EPIC-08 | **Points:** 5 | **Priority:** Must

**User Story:**
> As a parent,
> I want to see my child's pending and paid fee records,
> So that I know what I owe, avoid late charges, and have receipts for past payments.

**Acceptance Criteria:**
- [ ] Given I view fees, Then I see a list of all fee records: fee type, amount, due date, status (paid/pending/overdue)
- [ ] Given a fee is overdue (due_date < today and unpaid), Then it's highlighted in red
- [ ] Given I click "Download Receipt" on a paid fee, Then I get the payment receipt PDF
- [ ] Given all fees are paid, Then I see "All fees are up to date ✓"
- [ ] Given there are pending fees, Then total outstanding is shown prominently at the top

**Dependencies:** SMS-037 (payment recording), SMS-038 (receipt generation), SMS-041

---

#### Tech Specification — SMS-044

**Backend API:**
```
GET /api/v1/parent-portal/children/:id/fees
Response 200: {
  "data": {
    "student_id": 5,
    "total_due": 8500.00,
    "total_paid": 12000.00,
    "records": [
      {
        "id": 1, "fee_type": "Tuition Fee", "amount": 5000.00,
        "due_date": "2026-04-15", "paid_date": "2026-04-10",
        "status": "paid", "payment_id": 201, "receipt_url": "/api/v1/fees/payments/201/receipt"
      },
      {
        "id": 2, "fee_type": "Library Fee", "amount": 500.00,
        "due_date": "2026-06-01", "status": "overdue"
      }
    ]
  }
}
```

**Frontend:**
- Total due shown in a red `p-message` banner if > 0
- Fee records in `p-table` with status badge: green=paid, amber=pending, red=overdue
- "Download Receipt" button on paid rows

---

#### Tasks — SMS-044

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-044-01 | Implement `GET /api/v1/parent-portal/children/:id/fees` | BE | @backend-engineer | 1.5h |
| T-044-02 | Compute overdue status (compare due_date vs today) | BE | @backend-engineer | 0.5h |
| T-044-03 | Build fee status table with status badges | FE | @frontend-engineer | 2h |
| T-044-04 | Add total outstanding banner | FE | @frontend-engineer | 0.5h |
| T-044-05 | Wire receipt download button | FE | @frontend-engineer | 0.5h |
| T-044-06 | Test: pending, overdue, paid, receipt download, data isolation | QA | @qa-engineer | 1h |

---

### SMS-045: School Notice Board (Parent View)
**Epic:** EPIC-08 | **Points:** 3 | **Priority:** Must

**User Story:**
> As a parent,
> I want to see school announcements targeted to my role or my child's class,
> So that I stay informed about school events, holidays, and important updates.

**Acceptance Criteria:**
- [ ] Given school-wide announcements exist, Then I see them in the notice board
- [ ] Given class-specific announcements (targeted to Grade 5), Then only parents of Grade 5 children see them
- [ ] Given a new notice arrives, Then a badge shows on the Notice Board menu item
- [ ] Notices show: title, date, content, attachments (if any)
- [ ] Given a notice is older than 30 days, Then it appears in "Archived Notices" section

**Dependencies:** SMS-051 (announcements creation by admin), SMS-041

---

#### Tech Specification — SMS-045

**Backend API:**
```
GET /api/v1/parent-portal/notices?page=1&per_page=10
Role Required: parent
Returns: announcements targeted to 'parent' role OR to child's class_id

Response 200: {
  "data": {
    "notices": [
      { "id": 1, "title": "Parent-Teacher Meeting", "content": "...",
        "published_at": "2026-06-01", "target": "school-wide", "is_new": true }
    ],
    "meta": { "total": 12, "page": 1 }
  }
}
```

**Frontend:**
- Simple list with `p-timeline` or `p-card` list
- "New" badge on unread notices
- Expand/collapse full notice content

---

#### Tasks — SMS-045

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-045-01 | Implement `GET /api/v1/parent-portal/notices` with role + class targeting | BE | @backend-engineer | 1.5h |
| T-045-02 | Build notice board component with `p-timeline` | FE | @frontend-engineer | 1.5h |
| T-045-03 | Add unread badge on sidebar menu item | FE | @frontend-engineer | 0.5h |
| T-045-04 | Test: school-wide, class-targeted, archived, no notices | QA | @qa-engineer | 0.5h |
