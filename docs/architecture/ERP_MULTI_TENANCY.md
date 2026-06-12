# ERP Multi-Tenancy Architecture — Developer Guide

> **Sprint:** 2.5 — ERP Foundation  
> **Strategy:** Option B — Database-per-School  
> **Stack:** Flask + SQLAlchemy + SQLite · Angular 17 + PrimeNG

---

## 1. The Big Picture

Every school gets its **own isolated SQLite database file**. A shared
**master database** acts as the registry — it knows which schools exist
and where their database files live.

```
master.db  ←  registry of all schools + super admin accounts
│
├── school_greenwood.db   ←  all data for Greenwood High
├── school_riverside.db   ←  all data for Riverside Academy
└── school_demo.db        ←  demo / seed school
```

There is **no shared school data** — one school can never accidentally
read or write another school's rows.

---

## 2. Directory Layout

```
backend/
├── instance/
│   ├── master.db                   ← super admin users, school registry
│   └── schools/
│       ├── school_demo.db          ← one DB file per school
│       ├── school_greenwood.db
│       └── school_riverside.db
├── app/
│   ├── models/
│   │   ├── master/                 ← models bound to master.db
│   │   │   ├── school.py           ← School registry model
│   │   │   ├── super_admin.py      ← SuperAdmin model
│   │   │   └── super_admin_revoked_token.py
│   │   ├── user.py                 ← school-scoped models (all others)
│   │   ├── student.py
│   │   └── ...
│   ├── routes/
│   │   ├── superadmin_auth.py      ← /api/v1/superadmin/auth/*
│   │   ├── superadmin_schools.py   ← /api/v1/superadmin/schools/*
│   │   └── auth.py                 ← /api/v1/auth/* (school users)
│   ├── services/
│   │   └── superadmin_service.py   ← school provisioning logic
│   └── utils/
│       └── tenant.py               ← TenantMiddleware (core of multi-tenancy)
└── migrations/
    └── env.py                      ← Alembic patched to run on any DB file
```

---

## 3. Two Types of Database Models

### 3a. Master-bound models (`__bind_key__ = 'master'`)

These live in `master.db` only. Flask-SQLAlchemy routes all queries for
these models to the master database automatically via the bind key.

```python
# backend/app/models/master/school.py
class School(db.Model):
    __bind_key__ = 'master'          # ← tells SQLAlchemy to use master.db
    __tablename__ = 'schools'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    slug        = db.Column(db.String(50), unique=True, nullable=False, index=True)
    db_url      = db.Column(db.String(500), nullable=False)  # path to school's .db file
    is_active   = db.Column(db.Boolean, default=True, nullable=False)
    ...
```

`db_url` for a school named "greenwood" would be:
```
sqlite:///D:/Projects/SMS/backend/instance/schools/school_greenwood.db
```

### 3b. School-scoped models (no bind key)

Everything else — `User`, `Student`, `Teacher`, `Parent`, `RevokedToken`, etc.
These have no `__bind_key__` and exist inside each school's own database.

```python
# backend/app/models/user.py
class User(db.Model):
    # No __bind_key__ — lives in the school's DB
    __tablename__ = 'users'

    id    = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role  = db.Column(db.Enum('admin', 'teacher', 'student', 'parent'), ...)
    ...
```

---

## 4. Config: Two Database Connections

```python
# backend/config.py
class Config:
    # Default DB = demo school (or any school — used by Flask-Migrate)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/schools/school_demo.db'

    # master.db connected via SQLALCHEMY_BINDS
    SQLALCHEMY_BINDS = {
        'master': 'sqlite:///instance/master.db'
    }
```

Flask-SQLAlchemy uses these two connections at startup:
- `db.session` / `db.engine` → school_demo.db (default)
- `db.get_engine(bind='master')` → master.db

Master-bound models (`__bind_key__ = 'master'`) always use the master
connection. School-scoped models use whichever connection the middleware
provides at request time.

---

## 5. TenantMiddleware — The Core of Multi-Tenancy

This is the most important piece. Before **every HTTP request**, the
middleware inspects the JWT or login payload to determine which school
is making the request, then opens a SQLAlchemy session on that school's
database file and stores it in `flask.g.db`.

```python
# backend/app/utils/tenant.py

_engine_cache: dict = {}   # db_url → sessionmaker, cached for the lifetime of the process


def setup_tenant_db() -> None:
    """Flask before_request hook."""

    # TESTING: all unit tests share one in-memory DB — bypass tenant logic
    if current_app.config.get('TESTING'):
        g.db = db.session
        return

    # Super admin routes use master.db directly — no tenant DB needed
    if request.path.startswith('/api/v1/superadmin/'):
        return

    school_slug = _extract_school_slug()   # from JWT or login body
    if not school_slug:
        return

    school = School.query.filter_by(slug=school_slug, is_active=True).first()
    if not school:
        return

    Session = _get_session_factory(school.db_url)  # cached engine creation
    g.db = Session()                                # open session for THIS request


def teardown_tenant_db(exc):
    """Flask teardown_request hook — always close the session."""
    session = g.pop('db', None)
    if session:
        if exc:
            session.rollback()
        session.close()
```

### How `school_slug` is extracted

```python
def _extract_school_slug() -> str | None:
    auth_header = request.headers.get('Authorization', '')

    # Case 1: authenticated request — slug embedded in the JWT
    if auth_header.startswith('Bearer '):
        decoded = decode_token(auth_header[7:])
        return decoded.get('school_slug') or None

    # Case 2: login request — slug sent in the request body
    if request.path == '/api/v1/auth/login' and request.method == 'POST':
        data = request.get_json(silent=True) or {}
        return data.get('school_slug') or None

    return None
```

### Engine caching

```python
def _get_session_factory(db_url: str):
    if db_url not in _engine_cache:
        engine = create_engine(db_url, connect_args={'check_same_thread': False})
        _engine_cache[db_url] = sessionmaker(bind=engine)
    return _engine_cache[db_url]
```

The SQLAlchemy engine is **created once per unique db_url** and reused
across all requests for that school. Only the session (connection) is
opened and closed per request.

### Using `get_db()` in services and routes

Every service and route that touches school-scoped data uses `get_db()`
instead of `db.session` directly:

```python
# backend/app/utils/tenant.py
def get_db():
    return getattr(g, 'db', db.session)
    #              ^^^^^^^^^^^^^^^^^^^^
    # returns the tenant session when inside a school request,
    # falls back to db.session for unauthenticated routes

# Usage in a route:
from app.utils.tenant import get_db

user = get_db().query(User).filter_by(email=email).first()
get_db().add(new_record)
get_db().commit()
```

---

## 6. JWT: `school_slug` in Every Token

When a school user logs in, the `school_slug` is embedded into the JWT
as a custom claim. Every subsequent request carries the slug in the
token — the middleware reads it to know which database to open.

```python
# backend/app/routes/auth.py

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # 1. Validate the slug against master.db
    school_slug = data['school_slug'].lower().strip()
    school = School.query.filter_by(slug=school_slug, is_active=True).first()
    if not school:
        return error_response("School not found or inactive", status=404)

    # 2. Find user in THIS school's DB (g.db was already set by middleware)
    user = get_db().query(User).filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return error_response("Invalid email or password", status=401)

    # 3. Embed school_slug in the JWT
    claims = {'role': user.role, 'user_id': user.id, 'school_slug': school_slug}
    access_token  = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)

    return success_response(data={'access_token': access_token, ...})
```

**JWT payload for a school user:**
```json
{
  "sub": "42",
  "role": "admin",
  "user_id": 42,
  "school_slug": "greenwood",
  "exp": 1781195235
}
```

**JWT payload for a super admin:**
```json
{
  "sub": "sa:1",
  "role": "super_admin",
  "super_admin_id": 1,
  "exp": 1781195235
}
```

Note: no `school_slug` in the super admin token. The middleware skips
tenant setup for `/api/v1/superadmin/` routes and they use `db.session`
(which points to master.db via the bind key).

---

## 7. Request Lifecycle — Step by Step

```
Browser / Angular
       │
       │  GET /api/v1/students/  (Authorization: Bearer <JWT with school_slug=greenwood>)
       ▼
Angular dev proxy (localhost:4200)
       │
       │  forwards to localhost:5000 with all headers intact
       ▼
Flask
       │
       ├─ [before_request] setup_tenant_db()
       │       decode JWT → slug = "greenwood"
       │       School.query.filter_by(slug="greenwood") → db_url = ".../school_greenwood.db"
       │       open session on school_greenwood.db → g.db = Session()
       │
       ├─ [route handler] GET /api/v1/students/
       │       students = get_db().query(Student).all()
       │                  ^^^^^^^
       │                  uses g.db → reads from school_greenwood.db
       │                  100% isolated from other schools
       │
       ├─ return JSON response
       │
       └─ [teardown_request] teardown_tenant_db()
               session.close()
```

---

## 8. Super Admin vs School User — Two Separate Auth Systems

| Aspect | School User | Super Admin |
|---|---|---|
| Login endpoint | `POST /api/v1/auth/login` | `POST /api/v1/superadmin/auth/login` |
| Required fields | `email`, `password`, `school_slug` | `email`, `password` |
| JWT identity | `"42"` (user id) | `"sa:1"` (prefixed) |
| JWT `role` | `"admin"` / `"teacher"` etc. | `"super_admin"` |
| Token stored | `localStorage.sms_access_token` | `localStorage.sms_sa_access_token` |
| Revoked tokens table | `revoked_tokens` (school DB) | `super_admin_revoked_tokens` (master.db) |
| Tenant middleware | runs, opens school DB | skipped for `/superadmin/` paths |
| DB queried | school's isolated `.db` file | master.db via bind key |

### Token revocation routing

```python
# backend/app/__init__.py

@jwt_manager.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']

    if jwt_payload.get('role') == 'super_admin':
        # Check master.db blocklist
        return SuperAdminRevokedToken.is_jti_blocklisted(jti)

    # Check school's own blocklist via tenant session
    return RevokedToken.is_jti_blocklisted(jti)
```

---

## 9. Provisioning a New School

When the super admin creates a new school, three things happen atomically:

```python
# backend/app/services/superadmin_service.py

def provision_school(data: dict) -> tuple:

    # Step 1 — Check slug is unique in master.db
    if School.query.filter_by(slug=slug).first():
        return None, {'message': "Slug already taken", 'status': 409}

    # Step 2 — Compute the file path for the new DB
    db_path = os.path.join(SCHOOLS_DB_DIR, f'school_{slug}.db')
    db_url  = 'sqlite:///' + db_path

    # Step 3 — Create the School record in master.db (not committed yet)
    school = School(name=data['name'], slug=slug, db_url=db_url, ...)
    db.session.add(school)
    db.session.flush()   # get school.id without committing

    # Step 4 — Create the physical .db file with all school-scoped tables
    _create_school_db(db_url)

    # Step 5 — Seed the first admin user into the new DB
    _seed_school_admin(db_url, admin_email=data['admin_email'], ...)

    # Step 6 — Commit master.db record only if steps 4+5 succeeded
    db.session.commit()
```

### How `_create_school_db` works

```python
def _create_school_db(db_url: str) -> None:
    engine = create_engine(db_url)

    # Only create tables that are NOT bound to master.db
    school_tables = [
        t for t in db.metadata.sorted_tables
        if t.info.get('bind_key') != 'master'
    ]
    db.metadata.create_all(engine, tables=school_tables)

    # Stamp the Alembic version so future migrations know the DB is at head
    head_rev = ScriptDirectory.from_config(alembic_cfg).get_current_head()
    conn.execute("INSERT OR IGNORE INTO alembic_version VALUES (:rev)", rev=head_rev)
```

Result: a brand-new SQLite file with all the school-scoped tables
(`users`, `students`, `teachers`, `classes`, `attendance`, etc.) and the
Alembic version set to the current migration head.

---

## 10. Running Migrations on All School Databases

When a new migration is created (new table, new column), it needs to run
against **every school's database**, not just the default one.

```bash
# Create the migration as normal
flask db migrate -m "add phone_verified column to users"

# Run it on every active school's DB
flask db-upgrade-all
```

The `db-upgrade-all` command iterates all active schools, checks the
current Alembic revision in each DB, and runs `upgrade head` only on
those that are behind:

```python
# backend/app/cli.py

for school in School.query.filter_by(is_active=True).all():
    # Check current revision
    with create_engine(school.db_url).connect() as conn:
        current_rev = MigrationContext.configure(conn).get_current_revision()

    if current_rev == head_rev:
        print(f"[{school.slug}] already at head — skip")
        continue

    # Override the Alembic target URL and run upgrade
    cfg = AlembicConfig(alembic_ini)
    cfg.attributes['target_db_url'] = school.db_url   # ← key override
    alembic_command.upgrade(cfg, 'head')
```

The `target_db_url` attribute is read in `migrations/env.py` to bypass
the default Flask-Migrate URL and point Alembic at the school's file:

```python
# backend/migrations/env.py

def get_engine_url():
    override = config.attributes.get('target_db_url')
    if override:
        return override          # ← used by db-upgrade-all
    return get_engine().url      # ← used by normal flask db upgrade

def run_migrations_online():
    override_url = config.attributes.get('target_db_url')
    if override_url:
        connectable = create_engine(override_url)
        # ... run migrations against this specific DB file
        return
    # ... normal Flask-Migrate path
```

---

## 11. Frontend: Two Separate Auth Services

Angular uses two completely separate services so the super admin portal
and the school portal never interfere with each other.

```
localStorage keys
├── sms_access_token       ← school user JWT         (AuthService)
├── sms_refresh_token      ← school user refresh JWT  (AuthService)
├── sms_user               ← school user profile JSON (AuthService)
├── sms_school_slug        ← active school slug       (AuthService)
│
├── sms_sa_access_token    ← super admin JWT          (SuperAdminAuthService)
├── sms_sa_refresh_token   ← super admin refresh JWT  (SuperAdminAuthService)
└── sms_sa_user            ← super admin profile JSON (SuperAdminAuthService)
```

### School login (includes `school_slug`)

```typescript
// frontend/src/app/core/services/auth.service.ts

login(email: string, password: string, schoolSlug: string) {
  return this.http.post('/api/v1/auth/login', {
    email,
    password,
    school_slug: schoolSlug    // ← required; validated against master.db
  }).pipe(
    tap(resp => {
      localStorage.setItem('sms_access_token',  resp.data.access_token);
      localStorage.setItem('sms_school_slug',   schoolSlug);
      ...
    })
  );
}
```

### Super admin login (no `school_slug`)

```typescript
// frontend/src/app/core/services/superadmin-auth.service.ts

login(email: string, password: string) {
  return this.http.post('/api/v1/superadmin/auth/login', { email, password })
    .pipe(
      tap(resp => {
        localStorage.setItem('sms_sa_access_token', resp.data.access_token);
        localStorage.setItem('sms_sa_user', JSON.stringify(resp.data.super_admin));
      })
    );
}
```

### SchoolsService: manual Authorization header

The `SchoolsService` (used by SA portal) sets the Authorization header
manually with the SA token, bypassing the JWT interceptor which only
knows about school tokens:

```typescript
// frontend/src/app/core/services/schools.service.ts

private get authHeaders(): HttpHeaders {
  const token = this.saAuth.getAccessToken();   // reads sms_sa_access_token
  return token
    ? new HttpHeaders({ Authorization: `Bearer ${token}` })
    : new HttpHeaders();
}

getSchools(page = 1, perPage = 20) {
  return this.http.get('/api/v1/superadmin/schools', {
    params: new HttpParams().set('page', page).set('per_page', perPage),
    headers: this.authHeaders    // ← SA token explicitly set
  });
}
```

### JWT interceptor: school vs super admin

```typescript
// frontend/src/app/core/interceptors/jwt.interceptor.ts

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);   // school AuthService only

  // Auto-inject school token only when no Authorization header is set
  const token = auth.getAccessToken();   // reads sms_access_token
  const authReq = (token && !req.headers.has('Authorization'))
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;   // SA requests already have Authorization set — leave them alone

  return next(authReq).pipe(
    catchError(error => {
      if (error.status === 401
          && !req.url.includes('/auth/refresh')
          && !req.url.includes('/auth/logout')
          && !req.url.includes('/superadmin/')) {  // ← do NOT touch SA routes
        // ... school token refresh logic
      }
      return throwError(() => error);
    })
  );
};
```

---

## 12. Adding a New School-Scoped Feature (Checklist)

When you add a new module (e.g. Library Management) follow this pattern:

### Backend

1. **Create the model** — no `__bind_key__`, it lives in the school DB:
   ```python
   class Book(db.Model):
       __tablename__ = 'books'
       id    = db.Column(db.Integer, primary_key=True)
       title = db.Column(db.String(255), nullable=False)
       ...
   ```

2. **Generate the migration:**
   ```bash
   flask db migrate -m "add books table"
   ```

3. **Apply to all schools:**
   ```bash
   flask db-upgrade-all
   ```

4. **Write the service** — always use `get_db()`:
   ```python
   from app.utils.tenant import get_db

   class LibraryService:
       @staticmethod
       def get_books():
           return get_db().query(Book).all()   # queries the current school's DB
   ```

5. **Write the route** — same `get_db()` rule applies:
   ```python
   from app.utils.decorators import roles_required

   @library_bp.route('/books', methods=['GET'])
   @roles_required('admin', 'teacher')
   def list_books():
       books = LibraryService.get_books()
       return success_response(data=[b.to_dict() for b in books])
   ```

### Frontend

No special handling needed — the school JWT already carries `school_slug`,
so every API call automatically hits the correct school's database.

---

## 13. Common Mistakes to Avoid

| Mistake | Why it breaks | Fix |
|---|---|---|
| Using `db.session` instead of `get_db()` in a route | `db.session` points to school_demo.db always, ignoring the tenant | Always use `get_db()` |
| Querying `School` via `get_db()` | `School` is master-bound; `get_db()` returns the school tenant session | Use `School.query` or `db.session.query(School)` for master models |
| Running `flask db upgrade` after a migration | Only upgrades school_demo.db | Run `flask db-upgrade-all` to upgrade every school |
| Forgetting `school_slug` in login | TenantMiddleware cannot identify the school | Always include `school_slug` in `POST /api/v1/auth/login` |
| Storing SA token as `sms_access_token` | JWT interceptor would treat it as a school token | SA tokens go in `sms_sa_access_token` only |

---

## 14. Quick Reference

```bash
# Provision a new school via CLI
flask provision-school \
  --slug greenwood \
  --name "Greenwood High School" \
  --admin-email admin@greenwood.edu \
  --admin-password "Admin@1234"

# Apply pending migrations to all school DBs
flask db-upgrade-all

# Create a new migration after model changes
flask db migrate -m "describe the change"
flask db-upgrade-all
```

```
API namespaces
  /api/v1/superadmin/*     → super admin only (master.db)
  /api/v1/auth/*           → school users (tenant DB, needs school_slug)
  /api/v1/students/*       → school users (tenant DB)
  /api/v1/teachers/*       → school users (tenant DB)
  ... (all other modules)  → school users (tenant DB)
```
