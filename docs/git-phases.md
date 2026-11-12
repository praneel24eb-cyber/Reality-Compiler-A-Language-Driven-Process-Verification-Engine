# Phase-by-phase Git checkpoints

Implementation was paused at the owner's request on 12 November 2026 so the
existing work could be committed and pushed in methodology order, from the start.

The `phasewise-from-start` branch starts at the repository's original initial
commit. Its ten commits group the current files by responsibility. They are
reconstructed review checkpoints, not the original development chronology or ten
independently runnable releases. Shared modules span several methodology phases:
for example, `app/engine.py` implements verification and what-if simulation.
The existing published commits are preserved when this sequence is merged into
`main`; no force push or published-history replacement is used.

| Phase | Committed scope |
| --- | --- |
| 1 — Define scope | Project configuration, exclusions and this scope/history map |
| 2 — Workflow schema | Typed states, transitions, actors, conditions and source sentence spans |
| 3 — Multi-pass extraction foundations | Provider adapters, ChatGPT connection, document ingestion and provider tests |
| 4 — Defect detection | Draft/review pipeline, evidence and reference validation, objectives regression tests |
| 5 — Graph verification | Multigraph analysis, reachability, dead ends, bypass witnesses and invariants; shared simulation implementation |
| 6 — What-if simulation | System regression coverage for immutable scenarios and graph changes |
| 7 — Database and provenance | SQLite/PostgreSQL models, migrations, parent-linked revisions, encrypted Windows sessions and recovery |
| 8 — User interface | API integration, guided builder, responsive canvas, graphs/mindmaps, finished styling and browser checks |
| 9 — Evaluation checkpoint | Nine annotated synthetic cases, baseline comparison, metrics, runner and observed live results |
| 10 — Documentation and release checkpoint | README, methodology, operational documentation, existing CI and container preparation |

## Status when implementation was paused

- The existing complete test suite passed 97 tests before the latest benchmark
  additions. The three new benchmark tests also passed separately. No new full
  suite run was performed merely to package the commits.
- Desktop/mobile component checks passed in Chrome. The browser fixture does not
  substitute for a live provider test or comprehensive accessibility testing.
- The live benchmark finished all nine cases with both methods returning results.
  Its source, predictions, metrics and limitations are in
  `evaluation/run-2026-11-12.json`. Reviewed defect-category macro F1 was about
  0.630 versus 0.889 for the baseline: the result does **not** demonstrate overall
  improvement. Benchmark analysis and further tuning were paused.
- The local dependency audit reported no known vulnerabilities at the time run.
- Existing GitHub Actions logs identified Windows-specific `ctypes.WinDLL` and
  `msvcrt` typing as the cause of Linux mypy failures. The source now carries
  targeted platform annotations and local mypy passes.
- Python 3.11 hash-pinned runtime and development locks now feed CI and both
  container builds. CI now covers PostgreSQL migrations, browser checks, dependency
  audit and Windows DPAPI tests. The updated remote workflow has not yet completed.
- Docker is unavailable locally, so container builds remain unverified. No hosting
  deployment was requested for this round.
- Database files, OAuth registrations, encrypted sessions, downloaded source PDFs,
  virtual environments, caches and local logs are excluded from publication.

Phase commits record work that exists; they do not declare unfinished phases
complete. Application development remains on hold until the owner resumes it.
