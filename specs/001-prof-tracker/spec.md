# Feature Specification: ProfTracker

**Feature Directory**: `specs/001-prof-tracker`
**Created**: 2026-04-18
**Status**: Draft

---

## Overview

ProfTracker is a Windows desktop application that captures and tracks hero proficiency data from the Marvel Rivals game client. It reads proficiency information directly from the game screen, stores each hero's level and XP progress locally, and presents a clear, browsable view of the player's hero roster with proficiency progress.

---

## Problem Statement

Marvel Rivals players have no easy way to track or review their hero proficiency progress outside of navigating the in-game menus. There is no persistent history, no at-a-glance summary across all heroes, and no way to monitor improvement over time without manually checking each hero individually.

---

## Goals

- Automatically capture hero proficiency data from the running Marvel Rivals client
- Store and persist captured data locally across sessions
- Display a clear, browsable summary of all heroes and their proficiency progress

---

## Non-Goals

- No cloud sync or account integration
- No social or sharing features
- No modification of game files or network traffic
- No support for platforms other than Windows

---

## User Scenarios & Testing

**Scenario 1 — Run a capture session**
A user launches ProfTracker while Marvel Rivals is running. They click "Select Window" and click the game window to register it. They click "Start Session" — the app resizes to a compact overlay. The user navigates to a hero's Proficiency tab in-game, selects the hero name from the dropdown, and presses **2** (or clicks "Capture Proficiency"). The app reads the level and XP from fixed pixel regions on screen and logs the result. The user repeats for each hero, then clicks "Finish" to save the session and view results.

**Scenario 2 — Browse hero proficiency**
After a session, the user sees a list of all captured heroes. They select a hero and see its name, current level, XP progress, and a visual proficiency bar.

**Scenario 3 — Recapture after playing**
A user plays Marvel Rivals and gains proficiency on a hero. They return to ProfTracker, start a new session, recapture that hero. The updated proficiency values replace the previous ones.

**Scenario 4 — Window not detected**
A user tries to capture without a valid window selected. ProfTracker reports a clear error and does not proceed.

---

## Functional Requirements

| ID     | Requirement                                                                                              | Priority |
|--------|----------------------------------------------------------------------------------------------------------|----------|
| ID     | Requirement                                                                                              | Priority |
|--------|----------------------------------------------------------------------------------------------------------|----------|
| FR-001 | The application validates the selected game window is still alive before each capture                    | Must     |
| FR-002 | The user selects a hero from a dropdown and navigates to their Proficiency tab manually in-game          | Must     |
| FR-003 | The application captures hero level and XP from fixed pixel regions on the proficiency screen            | Must     |
| FR-004 | Captured hero records are validated before being saved (no partial or corrupt records persisted)         | Must     |
| FR-005 | Validated hero records are stored locally and available after application restart                        | Must     |
| FR-006 | The application displays a scrollable list of all captured heroes with their latest proficiency values   | Must     |
| FR-007 | Selecting a hero shows a detail view with name, level, XP, and a visual progress bar                    | Must     |
| FR-008 | The user can start and finish a capture session from the application UI, with a per-hero hotkey (2)      | Must     |
| FR-009 | The application shows a real-time log of capture activity during a session                               | Should   |
| FR-010 | A new capture overwrites existing data for heroes that are re-captured                                   | Must     |
| FR-011 | Heroes at maximum proficiency level are clearly indicated (e.g., "MAX" label)                           | Should   |

---

## Success Criteria

- Each individual hero capture (press 2 → result logged) completes within 3 seconds
- All hero records captured in a session are persisted with no data loss across restarts
- The hero browser loads and is interactive within 2 seconds of session completion
- Users can go from application launch to first capture in 3 or fewer interactions
- The application provides a clear error message when a capture fails or the window is lost

---

## Key Entities

| Entity           | Description                                                                          |
|------------------|--------------------------------------------------------------------------------------|
| Hero             | A Marvel Rivals hero with name, role, proficiency level, and XP value               |
| CaptureRun       | A single scan session, including timestamp, status, and count of heroes captured     |
| ProficiencyEntry | The level and XP recorded for a Hero during a specific CaptureRun                   |

---

## Assumptions

- The user runs Marvel Rivals on the same Windows machine as ProfTracker
- The game's hero proficiency screen layout is consistent and predictable enough for automated screen reading
- Proficiency values are numeric (level integer + XP integer with a known maximum per level)
- A single user owns and operates the application (no multi-user accounts)
- The application captures approximately 50 heroes per scan session

---

## Dependencies

- Marvel Rivals must be running and on-screen during capture
- Local persistent storage for hero records and capture history
- Screen reading capability (the application reads pixels/text from the game window)

---

## Out of Scope

- Cloud backup or sync
- Notifications or scheduled scans
- Exporting data to external formats
- Support for multiple game accounts or profiles
