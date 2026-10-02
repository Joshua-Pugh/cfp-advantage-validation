# CFP Advantage Validation
Public validation archive for CFP Advantage. Every published projection is preserved before kickoff and graded after games to provide transparent, season-long accountability.

This repository contains only published outputs and grading artifacts. It does not expose proprietary model code or formulas.

## Independent replication

The [Independent Replication Kit](replication/README.md) provides a one-command,
standard-library verifier for the complete public population. It checks archive
hashes, designated receipt metadata, final-score arithmetic, winner grades, margin
errors, weekly and season summaries, and transparent same-game baselines. The kit
does not disclose proprietary model formulas or claim an independent review that
has not occurred.

## 2026 release note

Weeks 1–3 remain preserved under the original `2026.v1` release. A corrected
opponent-adjustment system is used prospectively beginning with Week 4 under
`2026.v2`; earlier receipts were not rewritten. Because the model specification
changed during the season, 2026 is tracked as a development-validation season and
clean prospective validation restarts in 2027.
