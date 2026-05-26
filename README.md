# ProficiencyTracker for Marvel Rivals

Automatically scans and tracks hero proficiency levels across sessions, with XP progression charts and data export.

---

## Requirements

- **Windows 10/11**
- **Marvel Rivals** installed and running
- **Interception driver** — required for Auto Scan only
  - Download: https://github.com/oblitum/Interception
  - Run the installer as Administrator, then reboot

OCR is built into the app — no separate install needed.

---

## Installation

1. Download `ProfTracker-windows.zip` from the [latest release](../../releases/latest)
2. Extract the zip anywhere on your computer
3. Run `ProfTracker.exe`

Your hero data is saved to `%APPDATA%\ProficiencyTracker\` and is preserved across updates.

---

## Usage

### Auto Scan

Auto Scan drives the game automatically and captures every hero in one pass.

**Before using Auto Scan:**
- Install the Interception driver (see Requirements above)
- Make sure Marvel Rivals is open on the Heroes grid screen
- Display Mode: **Windowed**, Resolution: **1920 × 1080**

**Steps:**
1. Select the game window using **Select Window**
2. Click **Auto Scan**
3. When prompted, **move your mouse once** then **press any key** — this registers your input devices
4. Switch to the Marvel Rivals window within 4 seconds
5. ProfTracker will navigate and capture all heroes automatically
6. Press **Backspace** at any time to cancel mid-scan

### Clipboard Scan

Update a single hero without the Interception driver:

1. In-game, navigate to the hero's **Proficiency** tab
2. Press **Alt+PrintScreen** to copy the game window to your clipboard
3. In ProfTracker, go to **HEROES**, right-click the hero's card, and choose **Scan from Clipboard**

### Viewing Results

- The **HEROES** tab shows all captured heroes with level, XP, and a progress bar
- Click a hero card to open the detail panel with XP history chart and velocity estimate
- The **TRAINING** tab spins a random hero that hasn't earned Lord (LV20) yet — filter by role
- Use the **⋯** menu in HEROES to export to Excel or import from a filled-in template

---

## Antivirus Warning

Some antivirus tools may flag `ProfTracker.exe` with detections such as:

- `Riskware.PyInstaller` (Yandex)
- `W32.Malware.7097E53A` (Bkav Pro)
- `Malicious` (SecureAge)

**These are false positives.** ProfTracker is packaged with PyInstaller, a standard Python bundling tool. Several antivirus engines flag all PyInstaller executables by default due to the packaging method, not because of any malicious code. The source code is fully available in this repository for review.

If your antivirus blocks the app, add `ProfTracker.exe` to its exclusion list.

---

## Data & Privacy

ProfTracker does not connect to the internet (except for update checks and Hero Wiki queries). All hero data is stored locally at:

```
%APPDATA%\ProficiencyTracker\proficiency_tracker.db
```
