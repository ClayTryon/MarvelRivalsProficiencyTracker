# ProficiencyTracker for Marvel Rivals

Automatically scans and tracks hero proficiency levels across sessions, with XP progression charts and data export.

---

## Requirements

- **Windows 10/11**
- **Marvel Rivals** installed and running
- **Tesseract OCR** — required for reading hero data
  - Download: https://github.com/UB-Mannheim/tesseract/wiki
  - Install with default settings (adds itself to PATH automatically)
- **Interception driver** — required for Auto Scan only
  - Download: https://github.com/oblitum/Interception
  - Run the installer as Administrator, then reboot

---

## Installation

1. Download `ProfTracker-windows.zip` from the [latest release](../../releases/latest)
2. Extract the zip anywhere on your computer
3. Run `ProfTracker.exe`

Your hero data is saved to `%APPDATA%\ProficiencyTracker\` and is preserved across updates.

---

## Usage

### Manual Scan

1. Launch **Marvel Rivals** and open the Heroes screen
2. Launch **ProfTracker** and click **Select Window**
3. Click anywhere on the Marvel Rivals window to target it
4. Navigate to a hero's proficiency screen in-game
5. Click **Start Scan** in ProfTracker to capture that hero

### Auto Scan

Auto Scan drives the game automatically and captures every hero in one pass.

**Before using Auto Scan:**
- Install the Interception driver (see Requirements above)
- Make sure Marvel Rivals is open on the Heroes grid screen

**Steps:**
1. Select the game window using **Select Window**
2. Click **Auto Scan**
3. When prompted, **move your mouse once** then **press any key** — this registers your input devices
4. Switch to the Marvel Rivals window within 4 seconds
5. ProfTracker will navigate and capture all heroes automatically

### Viewing Results

- The **hero list** on the left shows all captured heroes with level and XP
- Click a hero to see their detail panel with XP progress bar
- The **XP Progression** tab shows a chart of level history over time
- Use **Export** to save results to Excel

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

ProfTracker does not connect to the internet. All data is stored locally at:

```
%APPDATA%\ProficiencyTracker\proficiency_tracker.db
```
