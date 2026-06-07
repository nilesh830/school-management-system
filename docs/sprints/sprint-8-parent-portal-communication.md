# Sprint 8 — Parent Portal: Communication (Interactive)
**Scrum Master:** @scrum-master | **Dates:** Week 15–16
**Sprint Goal:** Enable parents to actively engage — apply leave for their child, message teachers directly, manage their profile, and receive real-time notifications — completing the Parent Portal loop.
**Velocity Target:** 29 pts | **Epic:** EPIC-09
**Dependencies:** Sprint 7 complete (parent dashboard, attendance, grades, fees working)

---

## Sprint Board

| Story | Title | Points | Assignee | Status |
|-------|-------|--------|----------|--------|
| SMS-046 | Leave Application Submission | 8 | @backend-engineer + @frontend-engineer | To Do |
| SMS-047 | Leave Application Tracking & Review | 5 | @backend-engineer + @frontend-engineer | To Do |
| SMS-048 | Parent-Teacher Messaging | 8 | @backend-engineer + @frontend-engineer | To Do |
| SMS-049 | In-App Notifications (Parent) | 5 | @backend-engineer + @frontend-engineer | To Do |
| SMS-050 | Parent Profile Management | 3 | @frontend-engineer | To Do |

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

**Frontend Component:**
```
parent-portal/leave/
├── leave-list.component.ts     # List of all leave applications
├── leave-form.component.ts     # Submit new leave (dialog/panel)
└── leave-status.component.ts   # Status badge component
```

**Leave Form Fields:**
- Child selector (PrimeNG `p-dropdown` — only parent's children)
- Leave type (`p-selectButton`: Sick / Family / Personal / Other)
- Date range (`p-calendar` range mode)
- Reason (`p-inputTextarea` — min 10 chars)
- Submit button with `p-confirmDialog`

---

#### Tasks — SMS-046

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-046-01 | Create Marshmallow `LeaveApplicationSchema` with date validation | BE | @backend-engineer | 1h |
| T-046-02 | Implement `LeaveService.submit()` with all business rule validations | BE | @backend-engineer | 2h |
| T-046-03 | Implement `POST /api/v1/leave-applications` route | BE | @backend-engineer | 0.5h |
| T-046-04 | Trigger teacher + admin notification on leave submission | BE | @backend-engineer | 1h |
| T-046-05 | Build leave submission form (child selector, date range, reason) | FE | @frontend-engineer | 3h |
| T-046-06 | Add leave list view with status badges | FE | @frontend-engineer | 1h |
| T-046-07 | Test: valid leave, past date, wrong child, missing reason, notifications sent | QA | @qa-engineer | 2h |
| T-046-08 | Security: parent cannot submit leave for unlinked student | SEC | @security-engineer | 0.5h |

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
- [ ] Given status=approved, Then the badge is green; rejected=red; pending=amber

**Acceptance Criteria (Admin/Teacher):**
- [ ] Given I am admin/teacher, When I GET `/api/v1/leave-applications?status=pending`, Then I see all pending leaves
- [ ] Given I approve/reject with remarks, Then status updates and parent is notified
- [ ] Given a leave is approved, Then the affected attendance dates are flagged as "leave" (not "absent")

**Dependencies:** SMS-046, SMS-049 (notifications)

---

#### Tech Specification — SMS-047

**Backend API:**
```
GET /api/v1/leave-applications                     → parent: own applications; admin/teacher: all
GET /api/v1/leave-applications?status=pending      → admin/teacher only
PUT /api/v1/leave-applications/:id/review
    Role Required: admin, teacher
    Body: { "status": "approved"|"rejected", "remarks": "Doctor's certificate required" }
    Response 200: { "data": { ...updated leave... } }
```

**Attendance Integration:** On approval, `LeaveService.review()` calls `AttendanceService.mark_as_leave(student_id, from_date, to_date)` — inserts attendance records with `status='leave'` for the date range.

**Admin/Teacher View:**
- `/admin/leave-applications` — filterable table (pending/approved/rejected)
- Quick approve/reject action buttons with remarks dialog

---

#### Tasks — SMS-047

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-047-01 | Implement `GET /api/v1/leave-applications` with role-based filtering | BE | @backend-engineer | 1h |
| T-047-02 | Implement `PUT /api/v1/leave-applications/:id/review` + attendance integration | BE | @backend-engineer | 2h |
| T-047-03 | Trigger parent notification on review decision | BE | @backend-engineer | 0.5h |
| T-047-04 | Build leave review table for admin/teacher | FE | @frontend-engineer | 2h |
| T-047-05 | Add approve/reject dialog with remarks input | FE | @frontend-engineer | 1h |
| T-047-06 | Test: parent tracking, admin review, attendance integration, notification | QA | @qa-engineer | 1.5h |

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
- [ ] Given I start a new conversation, Then I select the child and the message subject, and write my first message
- [ ] Given I send a message, Then the teacher receives an in-app notification
- [ ] Given I view my messages, Then I see conversation threads sorted by latest message
- [ ] Given a thread, When I open it, Then I see the full conversation history (oldest to newest)
- [ ] Given I send a reply, Then the other party sees it immediately on page refresh
- [ ] Given an unread message, Then the Messages menu badge shows count
- [ ] Parent can only message the class teacher of their linked child (not any teacher)

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
2. Find section's class teacher from `timetables` or assign class teacher from `sections.teacher_id`
3. Create `MessageThread` linking parent ↔ teacher ↔ child

**Frontend:**
```
parent-portal/messages/
├── thread-list.component.ts       # List of all conversations
├── thread-detail.component.ts     # Chat-style view of one thread
└── new-thread-dialog.component.ts # Start new conversation dialog
```

**UI Pattern:** Chat-style bubble layout:
- Parent messages: right-aligned, blue background
- Teacher messages: left-aligned, grey background
- `p-scrollPanel` to contain message history, auto-scroll to bottom

---

#### Tasks — SMS-048

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-048-01 | Implement thread creation — auto-resolve class teacher | BE | @backend-engineer | 2h |
| T-048-02 | Implement GET thread list + thread detail endpoints | BE | @backend-engineer | 1.5h |
| T-048-03 | Implement reply endpoint + mark-read endpoint | BE | @backend-engineer | 1h |
| T-048-04 | Trigger notification on new message/reply | BE | @backend-engineer | 0.5h |
| T-048-05 | Build thread list view with unread count badges | FE | @frontend-engineer | 2h |
| T-048-06 | Build chat-style thread detail with bubble layout | FE | @frontend-engineer | 2.5h |
| T-048-07 | Build new conversation dialog | FE | @frontend-engineer | 1h |
| T-048-08 | Test: send message, receive reply, unread badge, teacher can only see own threads | QA | @qa-engineer | 2h |

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
- [ ] Given a new school announcement is published, Then I receive a notification
- [ ] Given I have unread notifications, Then the bell icon in the header shows a count badge
- [ ] Given I click the bell, Then I see a dropdown list of recent notifications (last 20)
- [ ] Given I click a notification, Then I'm navigated to the relevant page and the notification is marked read
- [ ] Given I click "Mark all read", Then all notifications are cleared

**Dependencies:** SMS-044, SMS-046, SMS-047, SMS-048

---

#### Tech Specification — SMS-049

**Backend API:**
```
GET /api/v1/notifications?unread=true     → unread notifications for current user
GET /api/v1/notifications                 → all notifications (last 50)
PUT /api/v1/notifications/:id/read        → mark one as read
PUT /api/v1/notifications/read-all        → mark all as read
```

**Notification Triggers (server-side):**
| Event | Triggered By | Recipient |
|-------|-------------|-----------|
| Child marked absent | Attendance save | Parent(s) of student |
| Exam marks below 40% | Marks entry | Parent(s) of student |
| Fee overdue | Daily job (cron) | Parent(s) of student |
| Leave approved/rejected | Leave review | Parent who submitted |
| New announcement | Announcement publish | All targeted parents |
| New message received | Message send | Recipient user |

**Frontend:**
```typescript
// Notification bell component
@Component({ selector: 'app-notification-bell' })
export class NotificationBellComponent implements OnInit {
  unreadCount = 0;
  notifications: Notification[] = [];

  ngOnInit() {
    // Poll every 60 seconds (or use SSE/WebSocket in future)
    this.loadNotifications();
    interval(60000).subscribe(() => this.loadNotifications());
  }
}
```

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

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-049-01 | Implement `GET /api/v1/notifications` + `PUT /read` + `PUT /read-all` | BE | @backend-engineer | 1.5h |
| T-049-02 | Add `NotificationService.create()` call in AttendanceService on absent | BE | @backend-engineer | 1h |
| T-049-03 | Add notification trigger in MarksService for below-40% | BE | @backend-engineer | 0.5h |
| T-049-04 | Build notification bell dropdown component | FE | @frontend-engineer | 2h |
| T-049-05 | Implement 60s polling for unread count | FE | @frontend-engineer | 0.5h |
| T-049-06 | Implement navigation map (click → route) | FE | @frontend-engineer | 1h |
| T-049-07 | Test: all trigger events, mark read, count badge, navigation | QA | @qa-engineer | 1.5h |

---

### SMS-050: Parent Profile Management
**Epic:** EPIC-09 | **Points:** 3 | **Priority:** Must

**User Story:**
> As a parent,
> I want to update my contact information, emergency contact, and profile photo,
> So that the school always has accurate details to reach me.

**Acceptance Criteria:**
- [ ] Given I edit my profile, Then I can update: phone, alternate phone, address, occupation, emergency contact
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
**Never updatable by self:** `email`, `role`, `relationship_type` (admin only)

**Frontend:**
- `/parent/profile` — simple form with PrimeNG inputs
- Profile photo upload with preview using `p-fileUpload`

---

#### Tasks — SMS-050

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-050-01 | Implement `GET /api/v1/parents/me` + `PATCH /api/v1/parents/me` | BE | @backend-engineer | 1h |
| T-050-02 | Implement photo upload for parent profile | BE | @backend-engineer | 0.5h |
| T-050-03 | Build parent profile form page | FE | @frontend-engineer | 1.5h |
| T-050-04 | Test: update profile, photo upload, email locked, forbidden fields | QA | @qa-engineer | 0.5h |
