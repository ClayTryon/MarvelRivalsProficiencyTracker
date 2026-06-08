# Risk Register — ProfTracker Week 8
**Author:** Clay Tryon | **Course:** AI 410 | **Date:** June 2026

Likelihood scale: Low / Medium / High  
Impact scale: Low / Medium / High

---

## Active Risks

| ID | Risk | Likelihood | Impact | Current Mitigation | Week 9 Action |
|----|------|------------|--------|--------------------|---------------|
| R-001 | Fandom wiki DOM or MediaWiki API changes break the avatar/ability scraper | Medium | High | Scraper targets the MediaWiki `action=parse` and `action=query` endpoints (stable API, not rendered HTML) for structured data; BeautifulSoup used only for icon URL extraction | Add scraper unit tests using captured fixture HTML so regressions are caught before users see failures |
| R-002 | Groq free-tier rate limits block RAG queries during sync (bulk indexing hits API limits) | Medium | Medium | RAG index is built from locally-embedded vectors; Groq is only called at query time, not during indexing — bulk sync does not hit Groq | Add exponential backoff with jitter in `query_engine.py`; expose retry count in the status log |
| R-003 | PyInstaller bundle fails to include `rag_index/` path or HuggingFace cache, breaking RAG in the frozen exe | Low | High | `proftracker.spec` includes explicit `datas` entries; HuggingFace model is downloaded to user's cache on first query (not bundled) | Run a full frozen-build smoke test in CI against a release tag before shipping v1.3 |
| R-004 | OCR accuracy regresses when a Marvel Rivals patch changes the proficiency screen layout | High | Medium | Fixed pixel regions are calibrated per-resolution; capture retries once on failure; manual entry dialog provides a fallback path for any hero | Build an OCR regression test fixture using the existing `.temp/` proficiency screenshots so future layout changes are detected automatically |
| R-005 | Hero roster becomes stale after a game patch adds new heroes | High | Low | Wiki sync fetches the live Fandom hero list on demand; built-in `heroes.py` serves as a fallback if sync fails | Document the sync procedure in the user guide; wire a "new heroes available" banner when the wiki roster count exceeds the local count |
| R-006 | HuggingFace model download fails in restricted network environments (corporate proxy, air-gapped) | Low | High | Setup notes document the cache location (`~/.cache/huggingface/`); user can pre-download the model on a connected machine | Add a `PROFTRACKER_DISABLE_RAG=1` env-var flag that hides the HERO WIKI tab and skips model loading entirely |
| R-007 | EasyOCR or pytesseract version update breaks the capture pipeline | Low | Medium | `requirements.txt` pins minimum versions; pytest integration test covers the OCR pipeline end-to-end | Pin exact versions in the release build (`pip freeze > constraints.txt`) and add constraints file to PyInstaller CI step |
| R-008 | Wiki sync downloads excessive data (icons, HTML pages for 50+ heroes) and hits Fandom rate limits | Medium | Medium | Sync skips icons already present in `Icons/`; requests are sequential with natural latency between them | Add a configurable delay between requests (default 0.5 s) and log any HTTP 429 responses explicitly |

---

## Closed / Accepted Risks

| ID | Risk | Resolution |
|----|------|-----------|
| R-C01 | Database wiped by app update | Resolved in v1.0.6 — database moved to `%APPDATA%\ProficiencyTracker\` |
| R-C02 | Auto Scan driver (interception) crashes app on machines without the kernel driver | Resolved in v1.0.1 — interception lazy-loaded; app fully usable without driver |
| R-C03 | `heroes.py` hardcoded list becomes outdated | Resolved in Week 8 — wiki sync writes `heroes.json` dynamically; `heroes.py` reads from it |
| R-C04 | GROQ_API_KEY missing silently crashes the app | Resolved — missing key surfaces as an in-chat error message (FR-020); capture and browse features work without it |
