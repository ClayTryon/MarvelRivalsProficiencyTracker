# Prompt Log — ProfTracker Feature Workflow

> **Note:** This workflow was executed across multiple Claude Code sessions. The original prompt transcripts were not preserved. This document is a faithful reconstruction based on the current state of the generated artifacts (`spec.md`, `plan.md`, `tasks.md`).

This document reconstructs the `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` workflow
used to generate the design artifacts for the `001-prof-tracker` feature.

---

## Step 1 — `/speckit-specify`

**User prompt:**

> I want to build a Windows desktop app called ProfTracker that tracks hero proficiency data from Marvel Rivals. The app should let the user select the game window, then capture each hero's level and XP from the proficiency screen using screen reading (OCR). Data should be stored locally and browsable after a session. No cloud, no game file modification — just screen reading and local storage. Python + PyQt6.

**Skill output (summary):**

The skill generated `specs/001-prof-tracker/spec.md` with the following sections:

- **Overview**: Windows desktop app to capture and track Marvel Rivals hero proficiency via OCR; local SQLite storage; PyQt6 GUI.
- **Problem Statement**: No persistent cross-hero proficiency tracking exists outside in-game menus.
- **Goals**: Automated capture, local persistence, browsable summary.
- **Non-Goals**: No cloud sync, no social features, no game file modification, Windows only.
- **User Scenarios**: Four scenarios covering capture session, browsing results, recapture after play, and window-not-detected error handling.
- **Functional Requirements** (FR-001 through FR-011): Window validation, manual hero selection, fixed-region OCR capture, record validation, local persistence, hero list display, detail view with progress bar, hotkey session (key 2), real-time log, upsert on recapture, MAX indicator.
- **Success Criteria**: Per-hero capture under 3 seconds; no data loss across restarts; browser loads within 2 seconds; first capture in ≤ 3 interactions; clear error messages.
- **Key Entities**: Hero, CaptureRun, ProficiencyEntry.
- **Assumptions & Dependencies**: Same-machine Windows setup, consistent game UI layout, single-user.

---

## Step 2 — `/speckit-plan`

**User prompt:**

> /speckit-plan

**Skill output (summary):**

The skill generated `specs/001-prof-tracker/plan.md` with the following sections:

- **Technical Context**: Python 3.11+, PyQt6 ≥ 6.6, EasyOCR for level (italic font), pytesseract `--psm 6` for XP, `PIL.ImageGrab` for screen capture, pywin32 for window management, SQLite via `sqlite3`, pytest + pytest-qt.
- **Constitution Check**: All six project principles verified — Hero Data Integrity, Progression Transparency, TDD, Independent Incremental Delivery, Simplicity & Clarity First, Local-Only Constraint.
- **Project Structure**: Full `src/` and `tests/` tree defined — models, capture, storage, gui modules.
- **Implementation Phases**:
  - Phase 1 — Models & Storage (Hero dataclass, CaptureRun, SQLite schema, repository upsert)
  - Phase 2 — Capture Pipeline (clipboard/screen grab → EasyOCR + pytesseract → validate → store)
  - Phase 3 — Window Picker (transparent Qt overlay → win32 HWND resolution)
  - Phase 4 — GUI (ScanPanel, HeroBrowser, HeroDetailPanel, MainWindow, entry point)
- **Key Design Decisions**:
  - Two-engine OCR hybrid: EasyOCR handles the game's italic `LV##` font; pytesseract handles the XP fraction.
  - Fixed pixel regions: `_LEVEL_REGION = (510, 870, 600, 900)`, `_XP_REGION = (450, 910, 630, 970)`.
  - Hero upsert by name: recapture overwrites, no stale duplicates.
  - Compact 560×260 always-on-top overlay during session.

---

## Step 3 — `/speckit-tasks`

**User prompt:**

> /speckit-tasks

**Skill output (summary):**

The skill generated `specs/001-prof-tracker/tasks.md` with 20 dependency-ordered tasks across 5 phases:

| Phase | Tasks | Focus |
|-------|-------|-------|
| 0 | T-000, T-019 | Project setup: `requirements.txt`, `.gitignore`, `.temp/` debug image saving |
| 1 | T-001 – T-005 | Models & Storage: Hero validation tests → Hero model → CaptureRun → DB + repository |
| 2 | T-006 – T-012 | Capture Pipeline: OCR tests → pipeline integration test → clipboard capture → OCR module → window → navigator → full pipeline |
| 3 | T-013 | Window Picker: transparent Qt overlay → win32 HWND resolution |
| 4 | T-014 – T-018 | GUI: HeroDetailPanel → HeroBrowser → ScanPanel + ScanWorker → MainWindow → entry point |

Each task specifies type (test / implementation / setup), explicit dependencies, and acceptance criteria. Test tasks (T-001, T-002, T-006, T-007) are scheduled before their corresponding implementation tasks per the TDD constitution principle.

All 20 tasks are marked `[X]` complete in the task order summary.

---

## Resulting Artifacts

| Artifact | Path |
|---|---|
| Feature spec | `specs/001-prof-tracker/spec.md` |
| Implementation plan | `specs/001-prof-tracker/plan.md` |
| Task list | `specs/001-prof-tracker/tasks.md` |
| Data model | `specs/001-prof-tracker/data-model.md` |
| Storage schema | `specs/001-prof-tracker/contracts/storage-schema.sql` |
| Quickstart / README | `specs/001-prof-tracker/quickstart.md` |
