# CFP Advantage Independent Replication Kit

This directory makes the public record easy to audit without exposing CFP
Advantage's proprietary scoring engine. It answers a narrow question: **do the
published receipts, final scores, and reported grades reconcile on the complete
designated population?**

Run the verifier from the repository root with Python 3.10 or newer:

```text
python replication/verify.py
```

The command uses only Python's standard library. A successful run verifies:

- every canonical `2026/week-*/predictions.csv` row is represented in the
  population manifest;
- current archive files match the committed canonical SHA-256 inventory;
- designation metadata and original pregame receipt hashes are retained;
- final scores reproduce the stored winner and home-team margin;
- winner grades and absolute margin errors recompute exactly;
- weekly and season totals reproduce the committed summary; and
- simple baselines use the same graded games as CFP Advantage.

## Files

- `PROTOCOL.md`: population, source, grading, correction, and limitation rules.
- `CHANGELOG.md`: material 2026 receipt and specification changes.
- `verify.py`: public grading and integrity code.
- `outcomes.csv`: CFBD final-score snapshot for graded receipt games.
- `population.csv`: one row per designated prediction, including receipt and
  outcome provenance.
- `summary.json`: recomputed weekly, season, and baseline results.
- `manifest.json`: receipt metadata and current archive hashes.
- `checksums.sha256`: hashes for the source receipts, designations, corrections,
  and outcome snapshot consumed by the verifier.

The SHA-256 in a weekly `designation.md` identifies the original pregame receipt.
The public `predictions.csv` later gains grade fields, so its present-day file hash
is expected to differ. `manifest.json` records both values instead of treating that
difference as an integrity failure. Current text-file hashes normalize line endings
to LF so Windows and Linux clones produce the same digest.

## Claims this kit supports

If another person runs this code and confirms the output, the record has been
**independently replicated**. That does not mean the model has received an
independent methodological review. A design review requires access to additional
methodology and leakage controls, and prospective validation requires a frozen
specification over a future evaluation window.

Maintainers can refresh the score snapshot from the certified Product A schedule
artifact and rebuild the generated files with:

```text
python replication/verify.py --refresh-outcomes PATH_TO_TEAM_SCHEDULES.csv --write
```

The refresh command only imports completed games already marked `graded` in the
designated receipts. It does not grade pending games or change predictions.
