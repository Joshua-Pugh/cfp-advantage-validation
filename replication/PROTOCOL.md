# Replication Protocol

## Scope and population

The population is every row in the canonical `predictions.csv` under each
designated `2026/week-*` directory. Pending games remain in the population but are
excluded from completed-game performance metrics. Superseded receipts remain in
their archive for provenance and are not mixed into the canonical population.

The archive covers public Product A winner and margin projections. It does not
grade against-the-spread recommendations, totals, or private research lanes.

## Prediction and result orientation

`published_margin_home` and `actual_margin_home` use the same sign convention:

- positive: home team favored or won;
- negative: away team favored or won;
- zero: no point separation.

`model_lean` is the published outright winner. Final scores in `outcomes.csv` are
joined by CFBD `game_id` and team identity, rather than by row order.

## Outcome source

Final scores come from CollegeFootballData (CFBD) completed-game records ingested
by the certified CFP Advantage weekly pipeline. `outcomes.csv` identifies CFBD as
the provider and preserves the provider's game ID so a reviewer can independently
join the same games to CFBD or another score source. The verifier derives the
actual home margin and winner from the score pair and checks them against each
graded receipt row.

## Grading definitions

- **Winner correct:** `model_lean` equals the winner derived from the final score.
- **Winner accuracy:** correct winner grades divided by graded, non-tied games.
- **Absolute margin error:**
  `abs(actual_margin_home - published_margin_home)`.
- **Margin MAE:** mean absolute margin error across graded games.
- **Pending:** no completed outcome is graded and the game is excluded from
  completed-game performance metrics.
- **Final tie:** excluded from winner accuracy but eligible for margin error. This
  rule is included for completeness; modern FBS games do not ordinarily finish tied.
- **Push:** not applicable to Product A winner/margin grading. No sportsbook line
  or ATS result is used here.

The verifier rejects duplicate canonical game IDs, missing score rows for graded
games, outcome rows for unknown games, score/margin conflicts, winner conflicts,
grade conflicts, and summary or hash drift.

## Baselines

All baselines in `summary.json` use exactly the graded CFP Advantage population:

- **Home-team winner:** always select the listed home team.
- **Zero-margin:** predict an actual home margin of `0.0` for every game.
- **Home-by-3 margin:** predict an actual home margin of `+3.0` for every game.

These baselines are intentionally simple integrity checks, not claims that CFP
Advantage has beaten a strong public rating system. Elo, prior-season record, and
other rating comparisons should be added only with frozen, timestamped inputs and
the same eligibility rules. They must not be reconstructed from end-of-season data.

## Receipt hashes and chronology

Each weekly designation preserves the SHA-256 of the original pregame receipt and
its designation time. Grading appends result fields to the public CSV, which changes
the CSV's present-day file hash. The replication manifest therefore keeps:

1. the designation's original pregame receipt hash; and
2. the current graded archive file hash.

Git history supplies the public publication trail. A complete chronology audit may
also compare each designation timestamp with an independently sourced kickoff time.
This kit does not claim that such an external chronology audit has already occurred.
The current-archive checksum inventory canonicalizes text line endings to LF before
hashing, preventing Git's Windows line-ending conversion from creating false drift.

## Corrections and version boundaries

Corrections must preserve the prior artifact, document why it changed, and identify
the designated replacement. Week 2 follows that rule under `superseded/v1/` and
`correction.md`.

Weeks 1-3 use release `2026.v1`. Release `2026.v2` begins prospectively with Week 4
after opponent-adjustment and sparse-prior defects were corrected. Earlier receipts
were not rebuilt. Because the specification changed during 2026, the season is
described as development validation; a clean frozen prospective evaluation restarts
in 2027.

## Disclosure boundary

This kit discloses receipt inputs and outputs, football meaning, population rules,
grading code, version history, and limitations. It does not disclose proprietary
weights, thresholds, formulas, private research, credentials, or paid data.
