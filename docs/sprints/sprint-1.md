# Sprint 1 — Foundation & Authentication
**Scrum Master:** @scrum-master | **Dates:** Week 1–2
**Sprint Goal:** Bootstrap the project with working CI/CD, database setup, and complete JWT authentication so all other modules can be built on a secure foundation.
**Velocity Target:** 32 pts | **Epic:** EPIC-01

---

## Sprint Board

| Story | Title | Points | Assignee | Status |
|-------|-------|--------|----------|--------|
| SMS-001 | User Login with JWT | 5 | @backend-engineer | To Do |
| SMS-002 | Token Refresh & Logout | 3 | @backend-engineer | To Do |
| SMS-003 | Admin User Registration | 5 | @backend-engineer | To Do |
| SMS-004 | Role-Based Frontend Route Guards | 5 | @frontend-engineer | To Do |
| SMS-005 | Password Reset Flow | 8 | @backend-engineer + @frontend-engineer | To Do |
| SMS-006 | User Profile View & Edit | 6 | @frontend-engineer | To Do |
| — | DevOps: GitHub repo + CI/CD setup | — | @devops-engineer + @github-agent | To Do |
| — | DB: Initial schema migration | — | @database-engineer | To Do |

---

## Stories — Full Detail

---

### SMS-001: User Login with JWT
**Epic:** EPIC-01 | **Points:** 5 | **Priority:** Must

**User Story:**
> As a school user (admin/teacher/student/parent),
> I want to log in with my email and password,
> So that I can access the features relevant to my role.

**Acceptance Criteria:**
- [ ] Given valid credentials, When I POST `/api/v1/auth/login`, Then I receive `access_token` (15 min) + `refresh_token` (7 days) + user object with role
- [ ] Given invalid credentials, When I POST login, Then I receive HTTP 401 with `"Invalid email or password"` (no hint about which field is wrong)
- [ ] Given 5 failed login attempts in 1 minute, When I try again, Then I receive HTTP 429 (rate limited)
- [ ] Given I am logged in, When I open the app, Then I am redirected to my role-specific dashboard
- [ ] Given a deactivated user account, When I login, Then I receive HTTP 401

**Dependencies:** None (first story)

---

#### Tech Specification — SMS-001

**Backend API:**
```
POST /api/v1/auth/login
Body: { "email": string, "password": string }
Response 200: {
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "user": { "id": 1, "email": "admin@school.com", "role": "admin" }
  }
}
Response 401: { "success": false, "message": "Invalid email or password" }
Response 429: { "success": false, "message": "Too many requests" }
```

**JWT Payload (additional claims):**
```json
{ "role": "admin", "user_id": 1, "parent_id": null }
```
Note: `parent_id` is populated only when `role=parent`, used by Parent Portal routes.

**Database:** No new tables. Uses existing `users` table.

**Frontend Components:**
- `modules/auth/login/login.component.ts` — Reactive Form with email + password fields
- `modules/auth/login/login.component.html` — PrimeNG Card + InputText + Password + Button
- `core/services/auth.service.ts` — stores tokens in localStorage, exposes `currentUser()` signal
- `core/guards/auth.guard.ts` — redirects unauthenticated users to `/login`

**Security:** Rate limiting 5/minute on login endpoint (Flask-Limiter)

---

#### Tasks — SMS-001

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-001-01 | Implement `POST /api/v1/auth/login` in `routes/auth.py` | BE | @backend-engineer | 2h |
| T-001-02 | Add bcrypt password check in `User.check_password()` | BE | @backend-engineer | 1h |
| T-001-03 | Add `parent_id` to JWT additional_claims when role=parent | BE | @backend-engineer | 1h |
| T-001-04 | Apply `@limiter.limit("5/minute")` to login route | BE | @backend-engineer | 0.5h |
| T-001-05 | Write pytest: valid login, invalid login, rate limit, inactive user | QA | @qa-engineer | 2h |
| T-001-06 | Create `auth.service.ts` with `login()`, `logout()`, `currentUser()` | FE | @frontend-engineer | 2h |
| T-001-07 | Build `login.component` with PrimeNG form + validation | FE | @frontend-engineer | 2h |
| T-001-08 | Implement `auth.guard.ts` — redirect to /login if no token | FE | @frontend-engineer | 1h |
| T-001-09 | Role-based redirect after login (admin→/admin, teacher→/teacher, etc.) | FE | @frontend-engineer | 1h |

---

### SMS-002: Token Refresh & Logout
**Epic:** EPIC-01 | **Points:** 3 | **Priority:** Must

**User Story:**
> As a logged-in user,
> I want my session to stay alive while I'm active and log out cleanly,
> So that I don't get interrupted mid-task and my session is secured when I leave.

**Acceptance Criteria:**
- [ ] Given access token is expired, When Angular makes an API call, Then the HTTP Interceptor auto-refreshes and retries the original request
- [ ] Given refresh token is expired, When I try to refresh, Then I am logged out and redirected to login
- [ ] Given I click Logout, When the action completes, Then both tokens are cleared and the refresh token is revoked server-side
- [ ] Given I am logged out, When I try a protected route, Then I am redirected to login

**Dependencies:** SMS-001

---

#### Tech Specification — SMS-002

**Backend API:**
```
POST /api/v1/auth/refresh
Headers: Authorization: Bearer <refresh_token>
Response 200: { "data": { "access_token": "eyJ..." } }

POST /api/v1/auth/logout
Headers: Authorization: Bearer <access_token>
Body: { "refresh_token": "eyJ..." }
Response 200: { "message": "Logged out successfully" }
```

**Token Revocation:** Add `revoked_tokens` table with `jti` (JWT ID) column. `@jwt.token_in_blocklist_loader` checks this on every request.

**Frontend:**
- `core/interceptors/jwt.interceptor.ts` — intercepts 401 → refreshes → retries
- On refresh failure → call `auth.service.logout()` → navigate to `/login`

---

#### Tasks — SMS-002

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-002-01 | Implement `POST /api/v1/auth/refresh` | BE | @backend-engineer | 1h |
| T-002-02 | Create `revoked_tokens` table + model | DB | @database-engineer | 1h |
| T-002-03 | Implement `POST /api/v1/auth/logout` — adds JTI to blocklist | BE | @backend-engineer | 1.5h |
| T-002-04 | Register `@jwt.token_in_blocklist_loader` in app factory | BE | @backend-engineer | 0.5h |
| T-002-05 | Build JWT HTTP Interceptor with auto-refresh + retry logic | FE | @frontend-engineer | 3h |
| T-002-06 | Test: logout revokes token, expired refresh redirects | QA | @qa-engineer | 1.5h |

---

### SMS-003: Admin User Registration
**Epic:** EPIC-01 | **Points:** 5 | **Priority:** Must

**User Story:**
> As a school admin,
> I want to create user accounts for teachers, students, and parents,
> So that each person can log in with the correct role and access level.

**Acceptance Criteria:**
- [ ] Given I am admin, When I POST `/api/v1/users`, Then a user is created with hashed password and correct role
- [ ] Given an email already exists, When I try to register, Then I receive HTTP 409 Conflict
- [ ] Given a non-admin token, When I POST `/api/v1/users`, Then I receive HTTP 403
- [ ] Given I create a parent user, Then a `Parent` profile record is also auto-created and linked
- [ ] Given I create a student user, Then a `Student` shell record is created (enrollment fills details)

**Dependencies:** SMS-001

---

#### Tech Specification — SMS-003

**Backend API:**
```
POST /api/v1/users
Role Required: admin
Body: {
  "email": string,
  "password": string,
  "role": "admin"|"teacher"|"student"|"parent",
  "first_name": string,
  "last_name": string
}
Response 201: { "data": { "user": {...} } }
Response 409: { "message": "Email already registered" }
Response 403: { "message": "Insufficient permissions" }
```

**Auto-Profile Creation Logic (in UserService):**
- `role=parent` → create `Parent` record + link to user
- `role=teacher` → create `Teacher` shell record
- `role=student` → create `Student` shell record
- `role=admin` → user only, no profile record

**Frontend:** Admin panel form at `/admin/users/new` — role selector + name + email + auto-generated password option

---

#### Tasks — SMS-003

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-003-01 | Create `UserService.create_user()` with auto-profile logic | BE | @backend-engineer | 2h |
| T-003-02 | Implement `POST /api/v1/users` route with `@roles_required('admin')` | BE | @backend-engineer | 1h |
| T-003-03 | Write migration: `revoked_tokens` table | DB | @database-engineer | 0.5h |
| T-003-04 | Build user creation form in Angular admin module | FE | @frontend-engineer | 2h |
| T-003-05 | Test: create each role type, duplicate email, forbidden access | QA | @qa-engineer | 2h |
| T-003-06 | Security review: password strength, no plain-text in response | SEC | @security-engineer | 1h |

---

### SMS-004: Role-Based Frontend Route Guards
**Epic:** EPIC-01 | **Points:** 5 | **Priority:** Must

**User Story:**
> As a user of any role,
> I want to be shown only the features relevant to my role,
> So that I cannot accidentally or maliciously access other users' data.

**Acceptance Criteria:**
- [ ] Given role=admin, When I navigate to `/admin`, Then I see the admin layout and sidebar
- [ ] Given role=teacher, When I try to navigate to `/admin/users`, Then I am redirected to `/unauthorized`
- [ ] Given role=parent, When I navigate to `/parent/dashboard`, Then I see the Parent Portal layout
- [ ] Given role=student, When I try to navigate to `/parent`, Then I am redirected
- [ ] Given unauthenticated user, When I navigate to any protected route, Then I am redirected to `/login`

**Dependencies:** SMS-001, SMS-002

---

#### Tech Specification — SMS-004

**Guards:**
```typescript
// core/guards/role.guard.ts
export const roleGuard = (allowedRoles: string[]): CanActivateFn => {
  return (route, state) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const user = auth.currentUser();
    if (!user) { router.navigate(['/login']); return false; }
    if (!allowedRoles.includes(user.role)) {
      router.navigate(['/unauthorized']); return false;
    }
    return true;
  };
};
```

**Route Configuration:**
```typescript
const routes: Routes = [
  { path: 'admin', canActivate: [roleGuard(['admin'])],
    loadChildren: () => import('./modules/admin/admin.module') },
  { path: 'teacher', canActivate: [roleGuard(['admin','teacher'])],
    loadChildren: () => import('./modules/teacher/teacher.module') },
  { path: 'parent', canActivate: [roleGuard(['parent'])],
    loadChildren: () => import('./modules/parent-portal/parent-portal.module') },
  { path: 'student', canActivate: [roleGuard(['student'])],
    loadChildren: () => import('./modules/shared-student/student.module') },
];
```

---

#### Tasks — SMS-004

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-004-01 | Create `roleGuard` factory function | FE | @frontend-engineer | 1.5h |
| T-004-02 | Configure lazy-loaded routes for all 4 role modules | FE | @frontend-engineer | 2h |
| T-004-03 | Create role-specific layout shells (admin, teacher, parent, student) | FE | @frontend-engineer | 3h |
| T-004-04 | Build `/unauthorized` page component | FE | @frontend-engineer | 0.5h |
| T-004-05 | Test: each role accesses allowed/forbidden routes | QA | @qa-engineer | 2h |

---

### SMS-005: Password Reset Flow
**Epic:** EPIC-01 | **Points:** 8 | **Priority:** Should

**User Story:**
> As a user who forgot my password,
> I want to receive a password reset link via email,
> So that I can regain access to my account securely.

**Acceptance Criteria:**
- [ ] Given I submit my email, When I POST `/api/v1/auth/forgot-password`, Then I receive a success message (even if email not found — no enumeration)
- [ ] Given a valid reset token, When I submit a new password, Then my password is updated and the token is invalidated
- [ ] Given an expired token (>30 minutes), When I use it, Then I receive HTTP 400 "Token expired"
- [ ] Given a used token, When I try again, Then I receive HTTP 400
- [ ] New password must be ≥ 8 characters with at least one uppercase, one digit

**Dependencies:** SMS-001, SMS-003

---

#### Tech Specification — SMS-005

**Backend API:**
```
POST /api/v1/auth/forgot-password
Body: { "email": string }
Response 200: { "message": "If this email exists, a reset link has been sent" }

POST /api/v1/auth/reset-password
Body: { "token": string, "new_password": string }
Response 200: { "message": "Password reset successful" }
Response 400: { "message": "Invalid or expired token" }
```

**DB:** Add `password_reset_tokens` table: `(id, user_id, token_hash, expires_at, used_at)`

**Email:** Use `Flask-Mail` → send HTML email with reset link. Token = `secrets.token_urlsafe(32)`, hashed with SHA-256 before storing. Expires 30 min.

---

#### Tasks — SMS-005

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-005-01 | Create `password_reset_tokens` model + migration | DB | @database-engineer | 1h |
| T-005-02 | Implement forgot-password endpoint + token generation | BE | @backend-engineer | 2h |
| T-005-03 | Configure Flask-Mail + HTML email template | BE | @backend-engineer | 1.5h |
| T-005-04 | Implement reset-password endpoint with token validation | BE | @backend-engineer | 1.5h |
| T-005-05 | Build forgot-password + reset-password Angular pages | FE | @frontend-engineer | 2h |
| T-005-06 | Test: valid reset, expired token, used token, weak password | QA | @qa-engineer | 2h |

---

### SMS-006: User Profile View & Edit
**Epic:** EPIC-01 | **Points:** 6 | **Priority:** Should

**User Story:**
> As any logged-in user,
> I want to view and update my profile (name, phone, photo),
> So that my information is current and I feel ownership of my account.

**Acceptance Criteria:**
- [ ] Given I am logged in, When I GET `/api/v1/auth/me`, Then I see my profile info (no password)
- [ ] Given I submit valid updates, When I PATCH `/api/v1/auth/profile`, Then my name/phone is updated
- [ ] Given I upload a profile photo, When it's accepted, Then it's stored and the URL returned
- [ ] Given I try to change my role via the API, Then the field is ignored (role only changed by admin)

**Dependencies:** SMS-001

---

#### Tech Specification — SMS-006

**Backend API:**
```
GET  /api/v1/auth/me            → current user profile
PATCH /api/v1/auth/profile      → update name, phone, address (NOT role)
POST /api/v1/auth/profile/photo → upload profile photo (multipart/form-data)
```

**Frontend:** Profile page in each role layout's top-nav dropdown. PrimeNG `p-fileUpload` for photo.

---

#### Tasks — SMS-006

| # | Task | Layer | Assignee | Est. |
|---|------|-------|----------|------|
| T-006-01 | Implement `PATCH /api/v1/auth/profile` — whitelist updatable fields | BE | @backend-engineer | 1.5h |
| T-006-02 | Implement `POST /api/v1/auth/profile/photo` — save file, return URL | BE | @backend-engineer | 2h |
| T-006-03 | Build profile page component (shared across roles) | FE | @frontend-engineer | 2h |
| T-006-04 | Add profile photo upload with `p-fileUpload` | FE | @frontend-engineer | 1.5h |
| T-006-05 | Test: update profile, photo upload, role-change attempt | QA | @qa-engineer | 1.5h |

---

## Sprint 1 — DevOps & DB Setup Tasks

### DevOps Setup (not a story — sprint infra task)
| Task | Assignee |
|------|----------|
| Create GitHub repo with branch protection (main + develop) | @github-agent |
| Set up GitHub Actions CI (backend tests + frontend lint + security scan) | @devops-engineer |
| Create Docker Compose for local dev (backend hot-reload + frontend) | @devops-engineer |
| Create `.env.example` and document all env vars | @devops-engineer |

### Database Setup (not a story — sprint infra task)
| Task | Assignee |
|------|----------|
| Initialize Flask-Migrate (`flask db init`) | @database-engineer |
| Create initial migration: `users`, `revoked_tokens`, `password_reset_tokens` | @database-engineer |
| Write seed: 1 admin user, 2 teacher users, 3 student users, 2 parent users | @database-engineer |
