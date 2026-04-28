# Data Model: ProfTracker

**Date**: 2026-04-18
**Feature**: `specs/001-prof-tracker`

---

## Entities

### Hero

Represents a single Marvel Rivals hero and their current proficiency state as of the most recent capture.

| Field         | Type     | Constraints                          | Description                                      |
|---------------|----------|--------------------------------------|--------------------------------------------------|
| id            | INTEGER  | PRIMARY KEY AUTOINCREMENT            | Internal identifier                              |
| name          | TEXT     | NOT NULL, UNIQUE                     | Hero display name (e.g., "Iron Man")             |
| role          | TEXT     | NOT NULL                             | Hero role (e.g., "Duelist", "Vanguard", "Strategist") |
| level         | INTEGER  | NOT NULL, CHECK(level >= 1)          | Current proficiency level                        |
| xp            | INTEGER  | NOT NULL, CHECK(xp >= 0)             | XP within current level                         |
| xp_required   | INTEGER  | NOT NULL, CHECK(xp_required >= 0)    | XP needed to reach next level (0 if max level)  |
| is_max_level  | INTEGER  | NOT NULL DEFAULT 0 (boolean)         | 1 if hero is at maximum proficiency level       |
| capture_run_id| INTEGER  | NOT NULL, FOREIGN KEY → CaptureRun   | The scan that produced this record              |
| updated_at    | TEXT     | NOT NULL (ISO-8601 datetime)         | Timestamp of last update                        |

**Validation rules**:
- `name`: non-empty string, max 100 characters
- `role`: must be one of the known Marvel Rivals roles; stored as-is if unrecognised (soft validation)
- `level`: integer ≥ 1
- `xp`: integer ≥ 0; must be < `xp_required` unless `is_max_level = 1`
- `xp_required`: integer ≥ 0; must be 0 when `is_max_level = 1`
- All fields required; no partial records persisted (FR-004)

**Progress formula**:
```
progress_pct = 0.0                         if is_max_level
progress_pct = xp / xp_required * 100     otherwise
```

---

### CaptureRun

Represents a single scan session. Each scan produces one `CaptureRun` and zero-or-more `Hero` records linked to it.

| Field         | Type     | Constraints                          | Description                                      |
|---------------|----------|--------------------------------------|--------------------------------------------------|
| id            | INTEGER  | PRIMARY KEY AUTOINCREMENT            | Internal identifier                              |
| started_at    | TEXT     | NOT NULL (ISO-8601 datetime)         | When the scan began                              |
| completed_at  | TEXT     | NULLABLE (ISO-8601 datetime)         | When the scan finished (NULL if running/failed)  |
| status        | TEXT     | NOT NULL                             | One of: `running`, `completed`, `cancelled`, `failed` |
| hero_count    | INTEGER  | NOT NULL DEFAULT 0                   | Number of heroes successfully captured           |
| error_message | TEXT     | NULLABLE                             | Human-readable error if status = `failed`        |

**Status transitions**:
```
[created] → running → completed
                    → cancelled
                    → failed
```

---

## Relationships

```
CaptureRun 1 ──< Hero (capture_run_id)
```

- One `CaptureRun` produces many `Hero` records
- Deleting a `CaptureRun` cascades to delete its `Hero` records
- A `Hero` belongs to exactly one `CaptureRun`
- Uniqueness of `Hero.name` is enforced at application layer: a new scan UPSERTs by name (updates existing hero record, linking it to the new `CaptureRun`)

---

## Window Handle State (In-Memory Only)

The selected target window handle (`hwnd`) is **not persisted**. It is held in application memory for the lifetime of the session. The user is prompted to re-select the window each time the application starts.

| Field  | Type    | Description                                      |
|--------|---------|--------------------------------------------------|
| hwnd   | integer | Win32 window handle for the selected game window |
| title  | str     | Window title at selection time (display only)    |

---

## Clipboard Lifecycle (Ephemeral)

Images captured via the clipboard are **never written to disk**. The lifecycle is:

```
Focus game window
  → Send Alt+PrintScreen (clipboard write)
  → Read PIL.Image from clipboard
  → Clear clipboard (win32clipboard.EmptyClipboard)
  → Process image in memory
  → Discard image object
```

No image file is created or retained at any point.

---

## Storage Schema

See `contracts/storage-schema.sql` for the full DDL.
