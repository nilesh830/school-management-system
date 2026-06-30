# ADR-005: Fee Applicability — Optional/Opt-in Fees & Per-Student Billing (SMS-066)

Date: 2026-06-30
Status: Proposed
Author: Solution Architect

---

## Context

Fee generation today (`FeeService.generate_records_for_class`) bills **every active
student enrolled in the class** linked to a `FeeStructure`, at the **same flat amount**
(`fs.amount`), for every billing period. That is correct for **mandatory, class-wide**
fees (tuition, admission, exam) but wrong for **optional / opt-in** fees:

- **Optional fees** (transport, hostel, optional activities/clubs) must bill **only the
  students who subscribed**, not the whole class.
- **Transport** in particular has a **per-student amount**: fare varies by route /
  distance. It also cannot even be modelled today — `TransportRoute` has **no fare
  field**, and `_compute_periods` assumes one amount (`fs.amount`) for all students.

Current relevant shape (verified against source):

- `FeeStructure(class_id, academic_year_id, fee_type, amount, due_date, is_recurring,
  frequency ∈ {monthly,quarterly,annual,one_time}, is_active)` — **no applicability flag.**
- `FeeRecord(student_id, fee_structure_id, amount, discount, net_amount, due_date,
  period default "ONCE", status)` with `UniqueConstraint(student_id, fee_structure_id,
  period)`. This unique key is the **idempotency anchor** for generation.
- `StudentTransport(student_id, route_id, pickup_stop, drop_stop, academic_year_id,
  is_active)`, `UniqueConstraint(student_id, academic_year_id)` — the **natural
  transport opt-in table** (one active route per student per year).
- `Discount` is a per-`fee_record` line item; `net_amount = amount − Σ discounts`.
  There is **no `amount_override`** today; per-student amount is only achievable via the
  `amount` written at generation time.

**Multi-tenancy constraint (critical).** Tenancy is isolated-per-school. In production
this is realised as **schema-per-school in a single Postgres** (Railway), with the
`db-upgrade-all` CLI applying each migration to every school schema via
`schema_translate_map={None: schema}` (see `backend/app/cli.py`). Dev = Neon,
Prod = Railway, **separate databases**. The documented gotcha: a plain
`flask db upgrade` against a connection whose `search_path` is pinned to `public`
silently writes DDL to `public`, not the tenant schema — so per-schema DDL must be
routed explicitly. Any schema change here must be expressible as an Alembic migration
that the existing `db-upgrade-all` loop can apply to **every** tenant schema, and must
**default existing data to `mandatory` so current behaviour is unchanged**.

### The key open question

For **generic** optional fees (hostel, activities) there is **no opt-in table** today —
only `StudentTransport` exists, and it is transport-specific. We must choose:

- **(a)** Introduce a generic `student_fee_optin` (student ↔ fee_structure) join table
  **now**, covering transport *and* any optional fee uniformly.
- **(b)** Ship **v1 = applicability flag + transport-only** optional generation (driven
  by `StudentTransport`), and **defer** generic opt-in to v2.

---

## Decision

Adopt the **Applicability pattern**, keeping the class-wide blanket for mandatory fees,
and ship in **two phases** with a clean seam between them.

### 1. `FeeStructure.applicability` (the core switch)

Add `applicability VARCHAR(20) NOT NULL DEFAULT 'mandatory'`, constrained to
`('mandatory','optional')`.

- `mandatory` → **exactly today's behaviour** (bill all active enrolled students).
- `optional` → bill **only opted-in students**, where the opt-in source depends on the
  fee's `fee_type` link to transport (v1) or the generic opt-in table (v2).

This is the single most important, **hard-to-reverse** decision: it changes the meaning
of "generate" for a structure. We mitigate reversibility risk by **defaulting every
existing and new row to `mandatory`** — opting in to the new behaviour is explicit.

### 2. Transport as a first-class optional fee (v1)

A `FeeStructure` can be **linked to transport** rather than carrying a flat amount.

- Add `TransportRoute.fare NUMERIC(10,2) NULL` and
  `TransportRoute.fare_frequency VARCHAR(20) NOT NULL DEFAULT 'monthly'`
  (`∈ {monthly,quarterly,annual,one_time}`, same vocabulary as fee frequency).
- Add `FeeStructure.source_kind VARCHAR(20) NOT NULL DEFAULT 'flat'`
  (`∈ {flat,transport}`). `flat` = amount comes from `FeeStructure.amount` (all of
  today's fees). `transport` = **per-student amount comes from the student's active
  `StudentTransport.route.fare`**, and the structure's own `amount` is ignored
  (kept ≥ 0 only to satisfy NOT NULL; stored as `0`).

A `transport` structure is implicitly `applicability='optional'` (the service enforces
this), and its billed population is **the set of students with an active
`StudentTransport` row for that `academic_year_id`** — reusing the existing opt-in table
rather than inventing a new one for transport.

> **Decision on the open question: choose (b) for v1, (a) deferred to v2.**
> v1 = `applicability` flag + `source_kind='transport'` driven by `StudentTransport`.
> Generic `student_fee_optin` is **designed here** but **deferred** (see Phase 2 / Scope).
>
> **Trade-offs.**
> - (b) ships the highest-value, hardest-to-model case (transport, per-student fare)
>   **without a new table**, reusing a join table that already enforces one-route-per-
>   student-per-year. Smaller migration, less surface area across N tenant schemas, and
>   it unblocks the real billing pain now.
> - (b) leaves hostel/activities still billed class-wide **unless** an admin marks them
>   `optional` — in which case, in v1, an `optional` `flat` structure with **no opt-in
>   source** would bill **nobody** (safe-by-default: better to under-bill than to
>   wrongly bill the whole class). The UI must make this state obvious.
> - (a) is cleaner long-term (one mechanism for all optional fees) but adds a table +
>   CRUD + UI to manage opt-ins for fees that, today, the school has no workflow for. It
>   also raises a modelling question — should transport opt-in be migrated into it? —
>   that we do not want to answer under deadline. Deferring keeps the transport path
>   from being blocked on a generic design.

### 3. Per-student amount

For v1 the only per-student amount is the **transport fare** (read from the route at
generation time and written into `FeeRecord.amount`). We **also add an explicit
`FeeRecord.amount_override NUMERIC(10,2) NULL`** so an admin can adjust a single
student's billed amount (concession fare, partial-month) **without** abusing the
`Discount` mechanism (discounts are for reductions with an approver/audit trail; an
override is the *base* amount). When `amount_override` is set, generation/repair uses it
as the record's `amount`; otherwise `amount` is the computed amount (flat or fare).
`net_amount` stays `amount − Σ discounts`.

### 4. What stays the same (preserve invariants)

- `FeeRecord` unique key `(student_id, fee_structure_id, period)` is **unchanged** and
  remains the idempotency anchor.
- `_compute_periods` period math (labels, due dates, recurrence from `frequency`) is
  **unchanged**; only the **amount** and **which students** become parameterised.
- The standard envelope `{success, data, message, errors}` is unchanged.
- No raw SQL; SQLAlchemy ORM only. Business logic stays in services.

---

## Schema Changes (exact)

All columns added with `NOT NULL DEFAULT` (or `NULL`) so the migration is
**backfill-free for behaviour**: existing rows land on values that reproduce today's
behaviour exactly.

### `fee_structures` (ALTER)

| Column | Type | Null | Default | Constraint | Backfill of existing rows |
|---|---|---|---|---|---|
| `applicability` | `VARCHAR(20)` | NOT NULL | `'mandatory'` | `CHECK applicability IN ('mandatory','optional')` (`ck_fee_structures_applicability`) | server_default fills all existing rows → `'mandatory'` (no behaviour change) |
| `source_kind` | `VARCHAR(20)` | NOT NULL | `'flat'` | `CHECK source_kind IN ('flat','transport')` (`ck_fee_structures_source_kind`) | existing rows → `'flat'` |
| `transport_route_id` | `INTEGER` | NULL | — | FK → `transport_routes.id` (`fk_fee_structures_transport_route`), index `ix_fee_structures_transport_route_id` | existing rows → NULL |

Rule enforced in the **service** (not a DB constraint, to keep the cross-tenant
migration simple): `source_kind='transport'` ⇒ `applicability='optional'` and
`transport_route_id` **optional** (NULL = "any route the student is on"; non-NULL =
"only students on this specific route"). `source_kind='flat'` ⇒ `transport_route_id`
must be NULL.

### `transport_routes` (ALTER)

| Column | Type | Null | Default | Constraint | Backfill |
|---|---|---|---|---|---|
| `fare` | `NUMERIC(10,2)` | NULL | — | `CHECK fare IS NULL OR fare >= 0` (`ck_transport_routes_fare_nonneg`) | existing rows → NULL (route has no fare until admin sets it) |
| `fare_frequency` | `VARCHAR(20)` | NOT NULL | `'monthly'` | `CHECK fare_frequency IN ('monthly','quarterly','annual','one_time')` (`ck_transport_routes_fare_frequency`) | existing rows → `'monthly'` |

A route with `fare IS NULL` cannot back a transport fee structure — generation skips
such students and reports them (see algorithm), so a half-configured route never
silently bills 0.

### `fee_records` (ALTER)

| Column | Type | Null | Default | Constraint | Backfill |
|---|---|---|---|---|---|
| `amount_override` | `NUMERIC(10,2)` | NULL | — | `CHECK amount_override IS NULL OR amount_override >= 0` (`ck_fee_records_amount_override_nonneg`) | existing rows → NULL |

No new table in v1. (`student_fee_optin` is specified in **Deferred — v2** below, not
created now.)

### Migration mechanics (Alembic, multi-tenant safe)

- One revision, `down_revision = 'f3a9c1b2d4e7'` (current head, `fee_records_period`).
- Use `op.batch_alter_table(...)` for every ALTER (matches the repo's existing
  Postgres-and-SQLite-friendly style, e.g. `a1c2e3f40506`). Add columns **with
  `server_default`** for the NOT NULL ones so existing rows are populated atomically by
  the DDL — **no separate UPDATE backfill pass is needed**, which is what makes this
  safe to fan out across many tenant schemas.
- After the column is added, the model declares the same `default=`/Python default; the
  `server_default` may be dropped in a later cleanup migration if desired (not required).
- `downgrade()` drops the three FK/index/columns in reverse, drops the two
  `transport_routes` columns and the one `fee_records` column.

---

## Generation Algorithm Changes

`_compute_periods(fs, student, as_of)` is generalised so **amount** is resolved
per-student, and a new helper resolves **which students** and **what fare**. Idempotency
and the `(student_id, fee_structure_id, period)` unique key are untouched.

```text
generate_records_for_class(fee_structure_id, as_of=today):
    fs = load FeeStructure or 404

    # 1. Resolve the billed population + per-student amount source
    if fs.source_kind == 'transport':
        # optional, transport-driven: opt-in = active StudentTransport for the
        # structure's academic_year_id (optionally filtered to fs.transport_route_id)
        rows = query StudentTransport
                 join Student
                 where StudentTransport.is_active
                   and StudentTransport.academic_year_id == fs.academic_year_id
                   and Student.is_active
                   and (fs.transport_route_id is None
                        or StudentTransport.route_id == fs.transport_route_id)
        billed = [(st.student, st.route.fare, st.route.fare_frequency) for st in rows]
        # route.fare is the per-student amount; route.fare_frequency overrides fs.frequency
    elif fs.applicability == 'optional':   # flat optional (v1: no generic opt-in table)
        billed = []                        # safe-by-default: bills nobody, returns skipped_no_optin
    else:                                  # mandatory flat == TODAY's behaviour
        students = active students enrolled in fs.class_  # unchanged query
        billed = [(s, fs.amount, fs.frequency) for s in students]

    # 2. Existing (student_id, period) set for this structure — unchanged idempotency anchor
    existing = { (r.student_id, r.period) for r in FeeRecord
                 where fee_structure_id == fee_structure_id }

    generated = skipped = skipped_no_fare = 0
    for (student, unit_amount, freq) in billed:
        if fs.source_kind == 'transport' and unit_amount is None:
            skipped_no_fare += 1          # route has no fare configured — never bill 0
            continue
        for (label, due, amount) in _compute_periods_with(freq, unit_amount, student, as_of, fs):
            if (student.id, label) in existing:
                skipped += 1
                continue
            base = amount                  # flat: fs.amount ; transport: route.fare
            FeeRecord(student_id, fee_structure_id, amount=base, discount=0,
                      net_amount=base, due_date=due, period=label, status='pending')
            existing.add((student.id, label))
            generated += 1

    commit if generated > 0
    return {generated, skipped, skipped_no_fare, total_students: len(billed)}
```

`_compute_periods_with(freq, unit_amount, student, as_of, fs)` is `_compute_periods`
refactored to take `freq` and `unit_amount` as parameters instead of reading `fs.frequency`
/ `fs.amount` directly. Mandatory `flat` callers pass `(fs.frequency, fs.amount)` →
**byte-for-byte identical** to today. Transport callers pass
`(route.fare_frequency, route.fare)`.

**`amount_override` interaction (repair path).** When an admin sets
`amount_override` on an existing record, the record's `amount` and `net_amount` are
recomputed (`net = override − Σ discounts`) in `FeeService` at override time. Generation
never overwrites an existing `(student, period)` record (idempotency), so an override is
never clobbered by re-running generate.

**`run_recurring_catchup`** is unchanged in shape — it still loops active, non-`one_time`
structures and calls `generate_records_for_class`. Transport structures with recurring
`fare_frequency` are picked up automatically. (Note: a transport structure's effective
recurrence is `route.fare_frequency`; catch-up's `frequency != 'one_time'` pre-filter on
the *structure* should be relaxed to also include `source_kind='transport'` structures so
monthly transport fees auto-appear.)

---

## API Contract (standard envelope)

### Fee structure — `POST /api/v1/fee-structures` and `PUT /api/v1/fee-structures/{id}`

New optional request fields (Marshmallow `FeeStructureCreateSchema` / `UpdateSchema`):

| Field | Type | Default (create) | Rules |
|---|---|---|---|
| `applicability` | string | `'mandatory'` | one of `mandatory`,`optional` |
| `source_kind` | string | `'flat'` | one of `flat`,`transport` |
| `transport_route_id` | int / null | `null` | required-allowed only when `source_kind='transport'`; must reference an existing route. Forbidden (must be null) when `source_kind='flat'` |

Schema-level validation (`@validates_schema`):
- `source_kind='transport'` ⇒ force/accept `applicability='optional'`; `amount` becomes
  optional (defaults to `0`); `transport_route_id` optional.
- `source_kind='flat'` ⇒ `transport_route_id` must be null; existing `amount` rules apply.

Response `data` (FeeStructure `to_dict`) gains: `applicability`, `source_kind`,
`transport_route_id`. Example create response (201):

```json
{
  "success": true,
  "data": {
    "id": 42, "class_id": 7, "academic_year_id": 3,
    "fee_type": "Transport", "amount": 0.0, "due_date": null,
    "is_recurring": true, "frequency": "monthly",
    "applicability": "optional", "source_kind": "transport",
    "transport_route_id": 5, "is_active": true,
    "created_at": "2026-06-30T...", "updated_at": "2026-06-30T..."
  },
  "message": "Fee structure created successfully",
  "errors": null
}
```

### Transport route — `POST /api/v1/transport/routes` and `PUT /api/v1/transport/routes/{id}`

New optional request fields (`RouteCreateSchema` / `RouteUpdateSchema`):

| Field | Type | Default | Rules |
|---|---|---|---|
| `fare` | decimal / null | `null` | `>= 0` |
| `fare_frequency` | string | `'monthly'` | one of `monthly`,`quarterly`,`annual`,`one_time` |

Response `TransportRoute.to_dict` gains `fare` (float or null) and `fare_frequency`.

### Generate — `POST /api/v1/fee-structures/{id}/generate`

Request unchanged (no body). Response `data` gains `skipped_no_fare` and keeps
`generated`, `skipped`, `total_students`. `total_students` now means **billed
population** (opted-in count for optional/transport, enrolled count for mandatory).

```json
{
  "success": true,
  "data": { "generated": 18, "skipped": 4, "skipped_no_fare": 2, "total_students": 24 },
  "message": "Fee records generated successfully",
  "errors": null
}
```

### (New, optional) per-student amount override — `PATCH /api/v1/fee-records/{id}/amount`

Body `{ "amount_override": 450.00 }` (or `null` to clear). Admin only. Service recomputes
`amount`/`net_amount`, returns the updated `FeeRecord` in the envelope. **This endpoint is
v1.5/optional** — include only if frontend needs it for transport concessions; the column
is added in v1 regardless so no later migration is required.

---

## Phased Implementation Plan (ownership + dependency order)

**Phase 0 — agreement (Solution Architect).** Accept this ADR; confirm choice (b);
rename file to `adr-005-…` and update README.

**Phase 1 — v1: applicability flag + transport optional fees**

1. **Database Engineer** — single Alembic revision (`down_revision='f3a9c1b2d4e7'`):
   add the 3 `fee_structures` cols + FK/index, 2 `transport_routes` cols, 1 `fee_records`
   col, all with `server_default` for NOT NULL ones, via `batch_alter_table`. Provide
   `downgrade()`. *(blocks everything below)*
2. **Backend Engineer** — models: add fields + CHECK constraints to `FeeStructure`,
   `TransportRoute`, `FeeRecord` and extend each `to_dict`. Schemas: extend the two fee
   schemas + two route schemas with validation rules above. Service: refactor
   `_compute_periods` → `_compute_periods_with`, branch `generate_records_for_class` on
   `source_kind`/`applicability`, relax `run_recurring_catchup` filter, enforce
   `transport ⇒ optional`. Optionally add the `PATCH .../amount` endpoint + service. *(depends on 1)*
3. **Frontend Engineer** — fee-structure form: `applicability` select, `source_kind`
   select, conditional `transport_route_id` dropdown (hide `amount` when transport).
   Route form: `fare` + `fare_frequency`. Generate-result toast shows `skipped_no_fare`
   so admins see "2 students have no route fare set". Make the "optional flat bills
   nobody yet" state explicit. *(depends on 2 for response fields)*
4. **QA Engineer** — tests: mandatory generation unchanged (regression), transport
   generation bills only opted-in students at route fare, recurring transport catch-up,
   `skipped_no_fare` when route fare NULL, idempotent re-run, override path. 80%+.

**Phase 2 — v2 (deferred): generic opt-in** — see below.

### Multi-tenant production migration / rollout

1. Merge to `develop`; CI green. Migration reviewed for `batch_alter_table` +
   `server_default` correctness (so it works on SQLite dev *and* Postgres tenant schemas).
2. **Dev (Neon):** run `flask db upgrade-all` — confirm every active school schema moves
   to the new head (CLI reads/writes the version table per-schema via
   `version_table_schema` and routes DDL with `schema_translate_map`). Do **not** rely on
   a bare `flask db upgrade` (search_path pinned to `public` would mis-target — documented
   gotcha).
3. Smoke-test on a dev tenant: existing fee structures still `applicability='mandatory'`,
   generation output identical to before.
4. **Prod (Railway):** take a Postgres backup/snapshot first. Run `flask db upgrade-all`
   in a maintenance window. If any school errors, the CLI lists failures and exits
   non-zero — fix that schema (possibly apply the per-schema DDL directly per the gotcha)
   and re-run; the loop skips schemas already at head, so re-run is safe.
5. Provisioning of **new** schools already runs migrations on create — no extra step.
6. Rollback: `downgrade()` exists, but prefer rolling forward; dropping `applicability`
   after admins have created optional structures would lose intent. Treat
   `applicability`/`source_kind` as **hard-to-reverse once used in prod**.

---

## Scope: v1 (ship now) vs Deferred (v2)

**v1 — in scope (safe first slice):**
- `FeeStructure.applicability` (`mandatory`/`optional`), default `mandatory`.
- `FeeStructure.source_kind` (`flat`/`transport`) + `transport_route_id` FK.
- `TransportRoute.fare` + `fare_frequency`.
- `FeeRecord.amount_override` column (endpoint optional).
- Transport optional fees generated from active `StudentTransport` at route fare.
- Zero behaviour change for all existing (mandatory/flat) structures.

**v2 — deferred (designed, not built):**
- **`student_fee_optin`** join table: `(id, student_id FK, fee_structure_id FK,
  academic_year_id FK, amount_override NUMERIC(10,2) NULL, is_active BOOL,
  created_at, updated_at)`, `UniqueConstraint(student_id, fee_structure_id)`. Drives
  `optional`+`flat` fees (hostel, activities). Generation gains a third branch:
  `optional & flat` ⇒ bill students in `student_fee_optin`, using
  `optin.amount_override or fs.amount`.
- Optional: migrate transport opt-in to flow through the same table (or keep
  `StudentTransport` as the transport-specific projection — decide in v2 with usage data).
- Bulk opt-in/opt-out UI for non-transport optional fees.

**Why deferred is safe:** in v1 an `optional`+`flat` structure with no opt-in source
bills **nobody** (returns all `skipped_no_optin`), which is the safe failure mode — it
never wrongly bills the whole class. The UI surfaces this so admins aren't surprised.

---

## Consequences

**Benefits**
- Optional fees no longer mis-bill the whole class; transport finally modellable with
  per-student, per-route fares.
- Mandatory path is provably unchanged (same query, same amounts, same period math) —
  low regression risk.
- Reuses `StudentTransport` as the transport opt-in source — no new table, smaller
  cross-tenant migration.
- Idempotency and the `(student, structure, period)` unique key are preserved.
- `amount_override` gives a clean per-student amount knob distinct from `Discount`.

**Costs / risks**
- `applicability` and `source_kind` change the semantics of "generate" and are
  **hard to reverse once used in prod** — mitigated by `mandatory`/`flat` defaults.
- Migration must be applied to **every tenant schema** via `db-upgrade-all`; a
  half-applied fleet means inconsistent behaviour across schools — run in a maintenance
  window, verify all schools reach head.
- v1 leaves generic optional fees (hostel/activities) **unbillable until v2** unless
  modelled as transport — accepted trade-off, flagged in UI.
- Transport recurrence is now driven by `route.fare_frequency`, a second source of
  "frequency" alongside `FeeStructure.frequency`; documented, but a subtle place for bugs
  if future code reads `fs.frequency` for transport structures.

**Hard-to-reverse, flagged explicitly:** the `applicability`/`source_kind` semantics and
the decision to anchor transport billing on `StudentTransport` (vs a generic opt-in
table). Both are intentionally chosen to minimise migration blast radius now; revisit in
v2 before committing to a single opt-in mechanism platform-wide.
