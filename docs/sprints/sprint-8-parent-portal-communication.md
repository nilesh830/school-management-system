# Sprint 8 — Parent Portal: Communication (Interactive)
**Scrum Master:** @scrum-master | **Dates:** Week 15–16
**Sprint Goal:** Enable parents to actively engage — apply leave for their child, message teachers directly, manage their profile, and receive real-time notifications — completing the Parent Portal loop.
**Velocity Target:** 29 pts | **Epic:** EPIC-09
**Dependencies:** Sprint 7 complete (parent dashboard, attendance, grades, fees working)

> **How to invoke agents:**
> - Database work → `@database-engineer` (models, migrations, schema)
> - Backend work → `@backend-engineer` (routes, services, business logic, tests)
> - Frontend work → `@frontend-engineer` (Angular components, PrimeNG UI, HTTP services)

---

## Sprint Board

| Story | Title | Points | Agents |
|-------|-------|--------|--------|
| SMS-046 | Leave Application Submission | 8 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` |
| SMS-047 | Leave Application Tracking & Review | 5 | `@backend-engineer` → `@frontend-engineer` |
| SMS-048 | Parent-Teacher Messaging | 8 | `@database-engineer` → `@backend-engineer` → `@frontend-engineer` |
| SMS-049 | In-App Notifications (Parent) | 5 | `@backend-engineer` → `@frontend-engineer` |
| SMS-050 | Parent Profile Management | 3 | `@backend-engineer` → `@frontend-engineer` |

---

## Stories — Full Detail

---

### SMS-046: Leave Application Submission
**Epic:** EPIC-09 | **Points:** 8 | **Priority:** Must

**User Story:**
> As a parent,
> I want to submit a leave application for my child for specific dates with a reason,
> So that the school is formally notified of my child's planned absence and the absence is recorded correctly.

**Acceptance Criteria:**
- [ ] Given I am a parent, When I submit a leave application, Then it is created with status=pending
- [ ] Given `from_date` > `to_date`, Then HTTP 422 "End date must be after start date"
- [ ] Given `from_date` is in the past, Then HTTP 422 "Cannot apply leave for past dates"
- [ ] Given the leave is submitted, Then the class teacher and admin receive an in-app notification
- [ ] Given I have multiple children, Then I must select which child the leave is for
- [ ] Given I submit successfully, Then I see a confirmation with the leave ID and pending status

**Dependencies:** SMS-010 (parent linked to student), SMS-049 (notifications)

---

#### Tech Specification — SMS-046

**Backend API:**
```
POST /api/v1/leave-applications
Role Required: parent
Body: {
  "student_id": 5,
  "from_date": "2026-06-10",
  "to_date": "2026-06-11",
  "leave_type": "sick",
  "reason": "Child has fever"
}
Response 201: {
  "data": {
    "id": 1, "student_id": 5, "from_date": "2026-06-10",
    "to_date": "2026-06-11", "duration_days": 2,
    "leave_type": "sick", "reason": "Child has fever",
    "status": "pending", "created_at": "..."
  }
}
Response 422: { "errors": { "from_date": ["Cannot apply leave for past dates"] } }
Response 403: { "message": "You are not linked to this student" }
```

**Business Rules (enforced in LeaveService):**
1. `from_date` must be today or future
2. `to_date` >= `from_date`
3. `student_id` must be in parent's linked children (`student_parent`)
4. On success: create `Notification` for class teacher + admin

**Validation (Marshmallow schema):**
```python
class LeaveApplicationSchema(Schema):
    student_id = fields.Int(required=True)
    from_date = fields.Date(required=True)
    to_date = fields.Date(required=True)
    reason = fields.Str(required=True, validate=validate.Length(min=10, max=500))
    leave_type = fields.Str(validate=validate.OneOf(['sick','family','personal','other']))
```

**DB Schema:**
```
leave_applications: (id, student_id FK, parent_id FK, from_date DATE, to_date DATE,
                     leave_type ENUM['sick','family','personal','other'],
                     reason TEXT, status ENUM['pending','approved','rejected'],
                     reviewed_by FK→users.id, reviewed_at, reviewer_remarks TEXT, created_at)
```

**Frontend Components:**
```
parent-portal/leave/
├── leave-list.component.ts     # List of all leave applications with status badges
├── leave-form.component.ts     # Submit new leave (child selector, date range, reason)
└── leave-status.component.ts   # Reusable status badge
```

**Leave Form Fields:**
- Child selector (`p-dropdown` — only parent's linked children)
- Leave type (`p-selectButton`: Sick / Family / Personal / Other)
- Date range (`p-calendar` range mode)
- Reason (`p-inputTextarea` — min 10 chars)
- Submit with `p-confirmDialog`

---

#### Tasks — SMS-046

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-046-01 | Create `LeaveApplication` model + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-046-02 | Create Marshmallow `LeaveApplicationSchema` with date validation | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-046-03 | Implement `LeaveService.submit()` with all business rule validations | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-046-04 | Implement `POST /api/v1/leave-applications` route | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-046-05 | Trigger teacher + admin notification on leave submission | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-046-06 | Build leave submission form (child selector, date range, reason) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 3h |
| T-046-07 | Add leave list view with status badges | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-046-08 | Tests: valid leave, past date 422, wrong child 403, missing reason, notifications sent | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |

---

### SMS-047: Leave Application Tracking & Review
**Epic:** EPIC-09 | **Points:** 5 | **Priority:** Must

**User Story:**
> As a parent,
> I want to see the status of my submitted leave applications and receive notification when they are reviewed,
> So that I know whether my child's leave is approved before the date.

> As an admin or teacher,
> I want to review and approve/reject leave applications with remarks,
> So that leave is managed formally and parents are informed of decisions.

**Acceptance Criteria (Parent):**
- [ ] Given I view my leave applications, Then I see: child name, dates, reason, status, reviewer remarks
- [ ] Given a leave is approved/rejected, Then I receive an in-app notification
- [ ] Status badge: approved=green, rejected=red, pending=amber

**Acceptance Criteria (Admin/Teacher):**
- [ ] Given I am admin/teacher, `GET /api/v1/leave-applications?status=pending` returns all pending
- [ ] Given I approve/reject with remarks, Then status updates and parent is notified
- [ ] Given a leave is approved, Then the affected attendance dates are flagged as "leave"

**Dependencies:** SMS-046, SMS-049 (notifications)

---

#### Tech Specification — SMS-047

**Backend API:**
```
GET /api/v1/leave-applications                     → parent: own; admin/teacher: all
GET /api/v1/leave-applications?status=pending      → admin/teacher only
PUT /api/v1/leave-applications/:id/review
    Role Required: admin, teacher
    Body: { "status": "approved"|"rejected", "remarks": "..." }
```

**Attendance Integration:** On approval, calls `AttendanceService.mark_as_leave(student_id, from_date, to_date)`.

---

#### Tasks — SMS-047

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-047-01 | Implement `GET /api/v1/leave-applications` with role-based filtering | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-047-02 | Implement `PUT /api/v1/leave-applications/:id/review` + attendance integration | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-047-03 | Trigger parent notification on review decision | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-047-04 | Build leave review table for admin/teacher (filterable by status) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-047-05 | Add approve/reject dialog with remarks input | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-047-06 | Tests: parent tracking, admin review, attendance integration, notification | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |

---

### SMS-048: Parent-Teacher Messaging
**Epic:** EPIC-09 | **Points:** 8 | **Priority:** Should

**User Story:**
> As a parent,
> I want to send a direct message to my child's class teacher,
> So that I can discuss concerns privately without needing to call the school.

> As a teacher,
> I want to receive and reply to parent messages in an organized thread,
> So that communication is tracked and I can respond at a convenient time.

**Acceptance Criteria:**
- [ ] Given I start a new conversation, Then I select the child and write my first message
- [ ] Given I send a message, Then the teacher receives an in-app notification
- [ ] Given I view my messages, Then I see conversation threads sorted by latest message
- [ ] Given a thread, When I open it, Then I see the full conversation history (oldest to newest)
- [ ] Given I send a reply, Then the other party sees it on page refresh
- [ ] Given an unread message, Then the Messages badge shows count
- [ ] Parent can only message the class teacher of their linked child

**Dependencies:** SMS-010 (parent-student link establishes which teacher to contact), SMS-049

---

#### Tech Specification — SMS-048

**Backend API:**
```
GET  /api/v1/messages/threads                     → list all threads for current user
POST /api/v1/messages/threads                     → create new thread
     Body: { "child_id": 5, "subject": "About homework", "message": "..." }
GET  /api/v1/messages/threads/:thread_id          → get thread + all messages
POST /api/v1/messages/threads/:thread_id/reply   → add reply
     Body: { "message": "Thank you for reaching out..." }
PUT  /api/v1/messages/threads/:thread_id/read    → mark all as read
```

**Thread Creation Logic:**
1. Find child's current section (`student_sections` where `is_current=true`)
2. Resolve class teacher from `sections.class_teacher_id`
3. Create `MessageThread` linking parent ↔ teacher ↔ child

**DB Schema:**
```
message_threads: (id UUID, subject, parent_id FK, teacher_id FK, student_id FK,
                  created_at, last_message_at, is_archived)
parent_messages: (id, thread_id FK, sender_id FK→users.id, body TEXT,
                  is_read BOOL, created_at)
```

**Frontend Components:**
```
parent-portal/messages/
├── thread-list.component.ts       # List of all conversations
├── thread-detail.component.ts     # Chat-style view of one thread
└── new-thread-dialog.component.ts # Start new conversation dialog
```

**UI Pattern:** Chat-style bubble layout — parent messages right-aligned blue, teacher messages left-aligned grey.

---

#### Tasks — SMS-048

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-048-01 | Create `MessageThread` + `ParentMessage` models + migration | [`@database-engineer`](.claude/agents/database-engineer.md) | 1h |
| T-048-02 | Implement thread creation — auto-resolve class teacher from section | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |
| T-048-03 | Implement GET thread list + thread detail endpoints | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-048-04 | Implement reply endpoint + mark-read endpoint | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-048-05 | Trigger notification on new message/reply | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-048-06 | Build thread list view with unread count badges | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-048-07 | Build chat-style thread detail with bubble layout + `p-scrollPanel` | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2.5h |
| T-048-08 | Build new conversation dialog (child selector + subject + first message) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-048-09 | Tests: send message, receive reply, unread badge, teacher sees only own threads | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 2h |

---

### SMS-049: In-App Notifications (Parent)
**Epic:** EPIC-09 | **Points:** 5 | **Priority:** Must

**User Story:**
> As a parent,
> I want to receive in-app notifications for important events (child absent, low marks, fee due, leave approved, new message),
> So that I'm always informed without having to manually check every section.

**Acceptance Criteria:**
- [ ] Given my child is marked absent, Then I receive a notification within 5 minutes of attendance being saved
- [ ] Given a leave application is approved/rejected, Then I receive a notification with the remarks
- [ ] Given I have unread notifications, Then the bell icon shows a count badge
- [ ] Given I click the bell, Then I see a dropdown of recent notifications (last 20)
- [ ] Given I click a notification, Then I'm navigated to the relevant page and notification marked read
- [ ] Given I click "Mark all read", Then all notifications are cleared

**Dependencies:** SMS-027 (`Notification` model already created in Sprint 4)

---

#### Tech Specification — SMS-049

**Backend API:**
```
GET /api/v1/notifications?unread=true   → unread notifications for current user
GET /api/v1/notifications               → all notifications (last 50)
PUT /api/v1/notifications/:id/read      → mark one as read
PUT /api/v1/notifications/read-all      → mark all as read
```

**Notification Triggers:**
| Event | Triggered By | Recipient |
|-------|-------------|-----------|
| Child marked absent | `AttendanceService` | Parent(s) of student |
| Exam marks below 40% | `ExamService` | Parent(s) of student |
| Fee overdue | Daily job | Parent(s) of student |
| Leave approved/rejected | `LeaveService` | Parent who submitted |
| New announcement | `AnnouncementService` | All targeted parents |
| New message received | `MessageService` | Recipient user |

**Navigation Map (notification.reference_type → route):**
```typescript
const routes = {
  'attendance': '/parent/children/:ref_id/attendance',
  'exam_result': '/parent/children/:ref_id/grades',
  'fee': '/parent/children/:ref_id/fees',
  'leave': '/parent/leave-applications',
  'message': '/parent/messages',
  'announcement': '/parent/notices',
};
```

---

#### Tasks — SMS-049

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-049-01 | Implement `GET /api/v1/notifications` + `PUT /read` + `PUT /read-all` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |
| T-049-02 | Add `NotificationService.create()` call in `ExamService` for below-40% | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-049-03 | Add fee-overdue notification trigger (daily check or on payment list) | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-049-04 | Build notification bell dropdown component (unread badge + list) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 2h |
| T-049-05 | Implement 60s polling for unread count | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 0.5h |
| T-049-06 | Implement navigation map (click notification → route) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-049-07 | Tests: all trigger events, mark read, count badge, navigation | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1.5h |

---

### SMS-050: Parent Profile Management
**Epic:** EPIC-09 | **Points:** 3 | **Priority:** Must

**User Story:**
> As a parent,
> I want to update my contact information, emergency contact, and profile photo,
> So that the school always has accurate details to reach me.

**Acceptance Criteria:**
- [ ] Given I edit my profile, Then I can update: phone, alternate phone, address, occupation
- [ ] Given I upload a profile photo, Then it is displayed in the header avatar
- [ ] Given I try to change my email, Then the field is disabled (email changes require admin)
- [ ] Given I save successfully, Then a success toast confirms the update

**Dependencies:** SMS-041

---

#### Tech Specification — SMS-050

**Backend API:**
```
GET   /api/v1/parents/me          → current parent profile
PATCH /api/v1/parents/me          → update contact info (not email, not role)
POST  /api/v1/parents/me/photo    → upload profile photo
```

**Updatable fields:** `first_name`, `last_name`, `phone_primary`, `phone_secondary`, `occupation`, `address`
**Never self-updatable:** `email`, `role`, `relationship_type` (admin only)

---

#### Tasks — SMS-050

| # | Task | Agent File | Est. |
|---|------|-----------|------|
| T-050-01 | Implement `GET /api/v1/parents/me` + `PATCH /api/v1/parents/me` | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 1h |
| T-050-02 | Implement photo upload for parent profile | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
| T-050-03 | Build parent profile form page (editable fields + locked email) | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1.5h |
| T-050-04 | Add photo upload with preview using `p-fileUpload` | [`@frontend-engineer`](.claude/agents/frontend-engineer.md) | 1h |
| T-050-05 | Tests: update profile, photo upload, email locked, forbidden fields | [`@backend-engineer`](.claude/agents/backend-engineer.md) | 0.5h |
