# SMS — Frontend Architecture (Angular SPA)

**Stack:** Angular 17 (standalone components) · TypeScript 5.4 · PrimeNG 17 +
PrimeFlex 4 + PrimeIcons 7 · chart.js 4 · RxJS 7 · Angular Signals for state.

A single Angular SPA serves **five portals** — Admin, Teacher, Student, Parent,
and Super Admin — each with its own layout, navigation, route file, and role
guard. The backend is reached under `/api/v1/*` (proxied to `:5000` in dev).

---

## 1. Bootstrap & Configuration

| Concern | Where | Notes |
|---|---|---|
| Bootstrap | `src/main.ts` | `bootstrapApplication(AppComponent, appConfig)` |
| Providers | `src/app/app.config.ts` | `provideRouter(routes, withComponentInputBinding())`, `provideHttpClient(withInterceptors([jwtInterceptor]))`, `provideAnimations()` |
| Root routes | `src/app/app.routes.ts` | top-level routes + lazy-loaded portal route files |
| Global styles | `src/styles.scss` | PrimeNG theme + PrimeFlex utilities |
| Dev proxy | `proxy.conf.json` | `/api` → `http://localhost:5000` (`ng serve`) |
| Build | `angular.json` | `@angular-devkit/build-angular:application`; budgets 500 KB warn / 1 MB error |

Everything is **standalone components** (no NgModules) and **lazy-loaded** per
portal via `loadChildren` / `loadComponent`.

---

## 2. Layered Structure

```
src/app/
├── app.component.ts        ← shell (RouterOutlet)
├── app.config.ts           ← providers + interceptor wiring
├── app.routes.ts           ← top-level + lazy portal routes
│
├── core/                   ← singletons: auth, guards, interceptor, services, models
│   ├── guards/             ← authGuard, roleGuard, superAdminGuard
│   ├── interceptors/       ← jwt.interceptor.ts (attach token + 401 refresh)
│   ├── models/             ← User, ApiResponse<T>, …
│   └── services/           ← 15 API services (one per backend module)
│
├── shared/                 ← reusable UI (ProfileComponent, UnauthorizedComponent)
│
└── modules/                ← feature portals (lazy-loaded)
    ├── auth/               ← login, forgot-password, reset-password
    ├── admin/              ← admin-layout + ~30 pages
    ├── teacher/            ← teacher-layout + pages (reuses admin components)
    ├── student/            ← student-layout + read-only pages
    ├── parent-portal/      ← parent-layout (mobile-first) + own service
    └── superadmin/         ← superadmin-layout + schools management
```

---

## 3. Authentication — Two Independent Systems

The school portals and the super-admin portal use **separate** services and
**separate** localStorage keys so they never collide.

| | School users | Super admin |
|---|---|---|
| Service | `core/services/auth.service.ts` | `core/services/superadmin-auth.service.ts` |
| Login | `POST /api/v1/auth/login` `{ email, password, school_slug }` | `POST /api/v1/superadmin/auth/login` `{ email, password }` |
| Tokens | `sms_access_token`, `sms_refresh_token` | `sms_sa_access_token`, `sms_sa_refresh_token` |
| Profile | `sms_user` | `sms_sa_user` |
| Tenant | `sms_school_slug` (sent at login, pre-filled next time) | — (no tenant) |
| State | Angular `signal<User\|null>` + `computed` `isAuthenticated` | same pattern |

### JWT interceptor (`core/interceptors/jwt.interceptor.ts`)
- **Skips** public URLs (`/auth/login`, `/auth/forgot-password`,
  `/auth/reset-password`).
- Attaches `Authorization: Bearer <sms_access_token>` **only if** the request
  doesn't already carry an `Authorization` header.
- On **401**, calls `auth.refreshToken()` and retries — **except** for
  `/auth/refresh`, `/auth/logout`, and any `/superadmin/*` URL (prevents loops
  and leaves the SA portal alone).
- The super-admin `SchoolsService` sets its `Authorization` header **manually**
  from `SuperAdminAuthService`, bypassing the interceptor's school token.

> Tenancy is implicit on the frontend: the school JWT already carries
> `school_slug`, so the backend routes each call to the right schema. The SPA
> never sends a tenant header itself.

---

## 4. Routing & Guards

Top-level (`app.routes.ts`):

| Path | Component / Layout | Guards | Role |
|---|---|---|---|
| `/login`, `/forgot-password`, `/reset-password`, `/unauthorized` | auth/standalone pages | — | public |
| `/admin/**` | `AdminLayoutComponent` (`ADMIN_ROUTES`) | `authGuard` + `roleGuard(['admin'])` | admin |
| `/teacher/**` | `TeacherLayoutComponent` (`TEACHER_ROUTES`) | `authGuard` + `roleGuard(['admin','teacher'])` | teacher |
| `/student/**` | `StudentLayoutComponent` (`STUDENT_ROUTES`) | `authGuard` + `roleGuard(['student'])` | student |
| `/parent/**` | `ParentLayoutComponent` (`PARENT_ROUTES`) | `authGuard` + `roleGuard(['parent'])` | parent |
| `/superadmin/**` | `SuperadminLayoutComponent` (`SUPERADMIN_ROUTES`) | `superAdminGuard` | super_admin |
| `**` | redirect → `/login` | — | — |

Guards (`core/guards/`):
- **`authGuard`** — token present / `isAuthenticated()`, else → `/login`.
- **`roleGuard(roles[])`** — `user.role ∈ roles`, else → `/unauthorized`.
- **`superAdminGuard`** — SA authenticated, else → `/superadmin/login`.

> **Defense in depth:** route guards are first-pass UX only. The backend
> independently enforces role **and** tenant on every request. Several teacher/
> student pages reuse admin components; the API does the real filtering.

---

## 5. Portals at a Glance

| Portal | Layout | Nav style | Highlights |
|---|---|---|---|
| **Admin** | `AdminLayoutComponent` | sidebar (~19 items) | dashboard (KPIs + charts), students, teachers, classes/sections/subjects, academic years, timetable, attendance (mark/view/report), exams (marks/results), fees (structures/payment/ledger/defaulters), library, transport, announcements, leave review, reports (attendance/grades/fees with PDF/Excel export) |
| **Teacher** | `TeacherLayoutComponent` | sidebar (~6) | dashboard, attendance (mark/view/report), timetable — reuses admin components; backend scopes to the teacher |
| **Student** | `StudentLayoutComponent` | sidebar (~5) | dashboard, grades, attendance calendar, timetable, library — read-only |
| **Parent** | `ParentLayoutComponent` | **mobile-first tabs** | dashboard (all children), per-child attendance/grades/fees, leave applications, parent–teacher messaging, notices, profile; **notification bell** with unread badge |
| **Super Admin** | `SuperadminLayoutComponent` | sidebar (2) | multi-school dashboard, schools list / provision / detail-edit / activate-deactivate |

### Parent Portal routes (mobile-first)
```
/parent/dashboard
/parent/children/:id/attendance
/parent/children/:id/grades
/parent/children/:id/fees
/parent/leave-applications
/parent/messages   ·   /parent/messages/:threadId
/parent/notices
/parent/profile
```

### Super Admin routes
```
/superadmin/login            (no guard)
/superadmin/dashboard        ┐
/superadmin/schools          │ superAdminGuard
/superadmin/schools/new      │
/superadmin/schools/:id      ┘
```

---

## 6. Services → Backend Namespace Map

All services are `providedIn: 'root'`, use `HttpClient`, and type responses as
`ApiResponse<T>` (the standard `{ success, data, message, errors }` envelope).

| Service | Backend namespace |
|---|---|
| `AuthService` | `/api/v1/auth` |
| `SuperAdminAuthService` | `/api/v1/superadmin/auth` |
| `SchoolsService` | `/api/v1/superadmin/schools` |
| `StudentService` | `/api/v1/students` |
| `TeacherService` | `/api/v1/teachers` |
| `ClassesService` | `/api/v1/classes`, `/subjects`, `/sections`, `/academic-years` |
| `AttendanceService` | `/api/v1/attendance` |
| `ExamService` | `/api/v1/exams` |
| `FeeStructureService` | `/api/v1/fee-structures`, `/api/v1/fees` |
| `LibraryService` | `/api/v1/library` |
| `AnnouncementService` | `/api/v1/announcements` |
| `TimetableService` | `/api/v1/timetables` |
| `TransportService` | `/api/v1/transport` |
| `ReportService` | `/api/v1/reports` (+ PDF/Excel blob exports) |
| `DashboardService` | `/api/v1/dashboard` |
| `ParentPortalService` | `/api/v1/parent-portal`, `/api/v1/leave-applications`, `/api/v1/notifications`, `/api/v1/parents` |

---

## 7. Conventions

- **Standalone components** with explicit `imports: [...]` of the PrimeNG modules
  they use (`TableModule`, `DialogModule`, `ChartModule`, …).
- **Reactive Forms** for all input; validators mirror backend Marshmallow rules
  (e.g. the login `school_slug` regex).
- **Signals** for service state (`currentUser`, derived `isAuthenticated`);
  `computed` for derived values.
- **Lazy loading** for every portal — keeps the initial bundle within budget.
- **Charts** via PrimeNG `ChartModule` (chart.js) on dashboards and report pages.
- **Exports** (PDF/Excel) are fetched as blobs from `/reports/*/export`.

---

## 8. Request → Render Lifecycle

```
Component → Service.method()           e.g. StudentService.getStudents()
  → HttpClient.get('/api/v1/students')
  → jwtInterceptor adds Authorization: Bearer <school JWT (carries school_slug)>
  → (dev) proxy localhost:4200 → :5000
  → Flask routes to the school schema, returns { success, data:{ students, meta }, … }
  → Service maps ApiResponse<T> → component signal/state
  → PrimeNG table/chart renders
  (on 401 → interceptor refreshes the access token and retries once)
```

See [system-overview.md](system-overview.md) for the end-to-end picture and
[ERP_MULTI_TENANCY.md](ERP_MULTI_TENANCY.md) for how the backend resolves the
tenant schema.
