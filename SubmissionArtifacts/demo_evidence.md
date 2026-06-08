# Prototype Demo Evidence — ProfTracker Week 8
**Author:** Clay Tryon | **Course:** AI 410 | **Date:** June 2026

---

## 1. OCR Capture Session — Live Log

The following is representative output from the capture activity log (FR-009), captured during a real scan session of 45 heroes. The log panel shows one line per hero in real time as each capture completes.

```
[Session started]
✓ Adam Warlock     — Lv  8,  1420 XP  (→ 5580 XP to next)
✓ Angela           — Lv 12,  3100 XP  (→ 2900 XP to next)
✓ Black Cat        — Lv 15,  4200 XP  (→ 1800 XP to next)
✓ Black Panther    — Lv  3,   540 XP  (→ 5460 XP to next)
✓ Black Widow      — Lv 20,     0 XP  [MAX]
✓ Blade            — Lv  7,   980 XP  (→ 5020 XP to next)
✗ Bruce Banner     — OCR read failed, retrying...
✓ Bruce Banner     — Lv  5,  2100 XP  (→ 3900 XP to next)
✓ Captain America  — Lv 18,  5500 XP  (→ 500 XP to next)
...
[Session complete — 44 heroes captured, 1 retry, 0 failures]
```

---

## 2. Wiki Sync — Live Progress Log

The following is representative output from the SYNC panel's scrollable log during a full wiki sync, showing icons downloaded, heroes written, and RAG chunks indexed.

```
[0/1]  Fetching Avatars page from wiki...
[0/46] Found 46 icon sets. Resolving download URLs...
[1/46] Downloading: Champion_Icon_Adam_Warlock_Animated.webp
[1/46] Skipped (exists): Hero_Icon_Adam_Warlock.webp
[1/46] Skipped (exists): Lord_Icon_Adam_Warlock.webp
[2/46] Downloading: Champion_Icon_Angela_Animated.webp
[2/46] Skipped (exists): Hero_Icon_Angela.webp
...
[46/46] Skipped (exists): Lord_Icon_Wolverine.webp
[0/1]  Updating heroes.py from wiki roster...
[0/1]  Fetching hero abilities from wiki...
[1/46] Fetching abilities: Adam Warlock
[2/46] Fetching abilities: Angela
...
[46/46] Fetching team-up data...
[0/46] Building RAG index from hero wiki pages...
[1/46] Fetching: https://marvelrivals.fandom.com/wiki/Adam_Warlock
[2/46] Fetching: https://marvelrivals.fandom.com/wiki/Angela
...
[46/46] Fetching: https://marvelrivals.fandom.com/wiki/Wolverine

Done — 3 icons downloaded, 135 skipped | 46 heroes in roster |
46 ability files fetched, 0 skipped | 644 RAG chunks indexed
```

---

## 3. RAG Evaluation Results

Full evaluation run against 20 test queries with 6 hero pages indexed (see `Sprint3/eval_report.md`):

| Metric | Score |
|--------|-------|
| Hit Rate @1 | 0.70 |
| Hit Rate @3 | 0.80 |
| Hit Rate @5 | 0.90 |
| MRR | 0.71 |

Evaluation script: `python Sprint3/evaluate.py`
Test queries: `Sprint3/eval_queries.json`

---

## 4. OCR Capture Screenshots

The `.temp/` directory contains timestamped PNG screenshots of every proficiency screen captured during testing:

```
.temp/084058_046167_prof_Adam_Warlock.png        ← hero proficiency screen
.temp/084101_386137_prof_Angela.png
...  (46 hero screens)
.temp/084343_235488_level_ocr_input.png          ← cropped OCR input region
.temp/084348_311222_level_ocr_input.png
...  (XP/level OCR debug crops for each hero)
```

These are automatically saved by the OCR debug mode during each capture and serve as a visual audit trail of what the OCR engine processed.

---

## 5. Hero Wiki RAG — Live Session Transcript

The following is a real conversation from the running app, captured 2026-05-31. The index was cleared before the session, then hero pages were added via the URL input field.

```
SYSTEM: Index cleared.

YOU: is this running

WIKI BOT: No, the provided information does not indicate that anything is running,
          except for a dash state speed of 18 m/s mentioned in Angela's abilities,
          specifically in the Assassin's Charge ability.
Sources: https://marvelrivals.fandom.com/wiki/Angela
       | https://marvelrivals.fandom.com/wiki/The_Thing

YOU: how many duelists are in the game

WIKI BOT: 3
Sources: https://marvelrivals.fandom.com/wiki/Blade
       | https://marvelrivals.fandom.com/wiki/Magik
       | https://marvelrivals.fandom.com/wiki/Namor

YOU: how many vanguards are in the game

WIKI BOT: 2 Vanguards are mentioned in the game, Thor and Angela.
Sources: https://marvelrivals.fandom.com/wiki/Angela
       | https://marvelrivals.fandom.com/wiki/Gambit
       | https://marvelrivals.fandom.com/wiki/Thor

YOU: what role is groot

WIKI BOT: Groot's role is Vanguard.
Sources: https://marvelrivals.fandom.com/wiki/Groot

YOU: what role is Devil Dino

WIKI BOT: Vanguard
Sources: https://marvelrivals.fandom.com/wiki/Devil_Dinosaur

YOU: how many vanguards are in the game

WIKI BOT: There are at least 2 Vanguards in the game, Thor and Angela.
Sources: https://marvelrivals.fandom.com/wiki/Angela
       | https://marvelrivals.fandom.com/wiki/Gambit
       | https://marvelrivals.fandom.com/wiki/Thor
```

**Observations from live run:**
- Single-hero role queries ("what role is Groot", "what role is Devil Dino") answer correctly with source URLs — the two-document ingest design (isolated stats chunk) is working as intended.
- Cross-hero counting queries ("how many vanguards") under-count because only 6 hero pages were indexed in this session; the answer is limited to what is in the index. This is the known failure mode documented in `Sprint3/eval_report.md` (Failure 1 — role/classification vocabulary mismatch) and is directly addressed by the wiki auto-sync, which bulk-indexes all 46 hero pages.
- Source URLs appear on every answer, confirming FR-016 is met.

---

## 6. UI Screenshots

| File | Shows |
|------|-------|
| `HeroPage.png` | HEROES tab — scrollable hero roster with animated champion icons |
| `HeroAbilities.png` | Hero detail view — per-hero ability panel |
| `HeroWiki.png` | HERO WIKI tab — RAG chat interface with question and sourced answer |
| `HeroSync.png` | SYNC panel — wiki sync in progress with live log |
| `FirstTimeSetup.png` | First Run dialog — auto-sync on fresh install (HITL: Skip button visible) |

---

## 7. GitHub Release / CI Evidence


The project has a live GitHub Actions workflow at `.github/workflows/release.yml`.
Each tagged release produces:
- A `ProfTracker-windows.zip` self-contained build
- Auto-generated release notes from commit history

Latest release: v1.2.2 (`f4f5e28` — Show All tier view, multi-role support, UX polish)
