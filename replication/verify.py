#!/usr/bin/env python3
"""Reproduce the public CFP Advantage grading record without model internals."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SEASON = 2026
GENERATED = ("population.csv", "summary.json", "manifest.json", "checksums.sha256")
POPULATION_FIELDS = (
    "season", "week", "release_id", "receipt_version", "publication_status",
    "designated_at_utc", "designation_receipt_sha256", "canonical_archive_csv_sha256",
    "run_label", "published_at_utc", "game_id", "date", "away_team", "home_team",
    "model_lean", "published_margin_home", "published_margin_text", "grade_status",
    "away_score", "home_score", "actual_margin_home", "actual_winner",
    "winner_correct", "absolute_margin_error", "outcome_source",
)


def canonical_bytes(data: bytes) -> bytes:
    """Normalize Git-managed text so hashes are stable across operating systems."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(canonical_bytes(path.read_bytes())).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def designation_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}: `([^`]*)`$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"Missing {label!r} in designation")
    return match.group(1)


def release_id(week: int) -> str:
    return "2026.v1" if week <= 3 else "2026.v2"


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def rounded(value: Decimal, places: int = 6) -> float:
    quantum = Decimal(1).scaleb(-places)
    return float(value.quantize(quantum))


def refresh_outcomes(schedule_path: Path, receipt_rows: list[dict[str, str]]) -> None:
    schedule = read_csv(schedule_path)
    by_game_team = {(row["game_id"], row["team"]): row for row in schedule}
    outcomes: list[dict[str, str]] = []
    for row in receipt_rows:
        if row["grade_status"] != "graded":
            continue
        key = (row["game_id"], row["home_team"])
        source = by_game_team.get(key)
        if source is None:
            raise ValueError(f"No schedule score row for {key}")
        if source.get("team_score", "") == "" or source.get("opponent_score", "") == "":
            raise ValueError(f"Incomplete schedule score row for {key}")
        outcomes.append({
            "game_id": row["game_id"],
            "season": row["season"],
            "week": row["week"],
            "date": row["date"],
            "away_team": row["away_team"],
            "home_team": row["home_team"],
            "away_score": source["opponent_score"],
            "home_score": source["team_score"],
            "source_provider": "CollegeFootballData (CFBD)",
            "source_game_id": row["game_id"],
        })
    outcomes.sort(key=lambda row: (int(row["week"]), row["date"], row["game_id"]))
    fields = list(outcomes[0]) if outcomes else [
        "game_id", "season", "week", "date", "away_team", "home_team",
        "away_score", "home_score", "source_provider", "source_game_id",
    ]
    with (HERE / "outcomes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(outcomes)


def load_archive() -> tuple[list[dict[str, str]], list[dict[str, object]], list[Path]]:
    rows: list[dict[str, str]] = []
    receipts: list[dict[str, object]] = []
    source_paths: list[Path] = []
    seen: set[str] = set()
    for week_dir in sorted((ROOT / str(SEASON)).glob("week-*")):
        prediction_path = week_dir / "predictions.csv"
        designation_path = week_dir / "designation.md"
        if not prediction_path.exists() or not designation_path.exists():
            raise ValueError(f"Incomplete canonical week directory: {week_dir}")
        designation = designation_path.read_text(encoding="utf-8")
        week = int(designation_value(designation, "Week"))
        receipt_version = designation_value(designation, "Receipt version")
        status = designation_value(designation, "Publication status")
        designated_at = designation_value(designation, "Designated at UTC")
        original_hash = designation_value(designation, "Projection receipt SHA-256")
        supersedes = designation_value(designation, "Supersedes projection receipt SHA-256")
        archive_hash = sha256(prediction_path)
        week_rows = read_csv(prediction_path)
        for row in week_rows:
            if row["game_id"] in seen:
                raise ValueError(f"Duplicate canonical game_id: {row['game_id']}")
            seen.add(row["game_id"])
            row["_release_id"] = release_id(week)
            row["_receipt_version"] = receipt_version
            row["_publication_status"] = status
            row["_designated_at_utc"] = designated_at
            row["_designation_receipt_sha256"] = original_hash
            row["_canonical_archive_csv_sha256"] = archive_hash
            rows.append(row)
        receipts.append({
            "season": SEASON,
            "week": week,
            "release_id": release_id(week),
            "publication_status": status,
            "receipt_version": int(receipt_version),
            "run_label": designation_value(designation, "Run label"),
            "designated_at_utc": designated_at,
            "original_pregame_receipt_sha256": original_hash,
            "supersedes_pregame_receipt_sha256": None if supersedes == "-" else supersedes,
            "canonical_archive_csv_sha256": archive_hash,
            "games": len(week_rows),
        })
        source_paths.extend([designation_path, prediction_path, week_dir / "receipt.md"])
        correction = week_dir / "correction.md"
        if correction.exists():
            source_paths.append(correction)
        superseded = week_dir / "superseded"
        if superseded.exists():
            source_paths.extend(path for path in superseded.rglob("*") if path.is_file())
    return rows, receipts, sorted(source_paths)


def validate_and_build(rows: list[dict[str, str]], receipts: list[dict[str, object]]) -> tuple[list[dict[str, str]], dict[str, object]]:
    outcome_rows = read_csv(HERE / "outcomes.csv")
    outcomes = {row["game_id"]: row for row in outcome_rows}
    if len(outcomes) != len(outcome_rows):
        raise ValueError("Duplicate game_id in outcomes.csv")
    known_ids = {row["game_id"] for row in rows}
    unknown = set(outcomes) - known_ids
    if unknown:
        raise ValueError(f"Outcome rows do not belong to canonical receipts: {sorted(unknown)}")

    population: list[dict[str, str]] = []
    stats = defaultdict(lambda: {"published": 0, "graded": 0, "winner_eligible": 0, "correct": 0, "error": Decimal(0), "home_wins": 0, "zero_error": Decimal(0), "home3_error": Decimal(0)})
    for row in rows:
        week = int(row["week"])
        release = row["_release_id"]
        buckets = (stats["combined"], stats[f"week-{week:02d}"], stats[release])
        for bucket in buckets:
            bucket["published"] += 1
        outcome = outcomes.get(row["game_id"])
        out = {field: "" for field in POPULATION_FIELDS}
        out.update({
            "season": row["season"], "week": row["week"], "release_id": release,
            "receipt_version": row["_receipt_version"],
            "publication_status": row["_publication_status"],
            "designated_at_utc": row["_designated_at_utc"],
            "designation_receipt_sha256": row["_designation_receipt_sha256"],
            "canonical_archive_csv_sha256": row["_canonical_archive_csv_sha256"],
            "run_label": row["run_label"], "published_at_utc": row["published_at_utc"],
            "game_id": row["game_id"], "date": row["date"],
            "away_team": row["away_team"], "home_team": row["home_team"],
            "model_lean": row["model_lean"],
            "published_margin_home": row["published_margin_home"],
            "published_margin_text": row["published_margin_text"],
            "grade_status": row["grade_status"],
        })
        if row["grade_status"] == "graded":
            if outcome is None:
                raise ValueError(f"Missing outcome for graded game {row['game_id']}")
            if outcome["away_team"] != row["away_team"] or outcome["home_team"] != row["home_team"]:
                raise ValueError(f"Team identity mismatch for game {row['game_id']}")
            away_score = int(outcome["away_score"])
            home_score = int(outcome["home_score"])
            actual_margin = Decimal(home_score - away_score)
            actual_winner = row["home_team"] if actual_margin > 0 else row["away_team"] if actual_margin < 0 else "Tie"
            predicted_margin = Decimal(row["published_margin_home"])
            margin_error = abs(actual_margin - predicted_margin)
            winner_correct = actual_winner != "Tie" and row["model_lean"] == actual_winner
            if Decimal(row["actual_margin_home"]) != actual_margin:
                raise ValueError(f"Actual-margin conflict for game {row['game_id']}")
            if row["actual_winner"] != actual_winner:
                raise ValueError(f"Actual-winner conflict for game {row['game_id']}")
            if row["winner_correct"].lower() != str(winner_correct).lower():
                raise ValueError(f"Winner-grade conflict for game {row['game_id']}")
            if abs(Decimal(row["absolute_margin_error"]) - margin_error) > Decimal("0.000001"):
                raise ValueError(f"Margin-error conflict for game {row['game_id']}")
            out.update({
                "away_score": str(away_score), "home_score": str(home_score),
                "actual_margin_home": decimal_text(actual_margin), "actual_winner": actual_winner,
                "winner_correct": str(winner_correct),
                "absolute_margin_error": decimal_text(margin_error),
                "outcome_source": outcome["source_provider"],
            })
            for bucket in buckets:
                bucket["graded"] += 1
                bucket["winner_eligible"] += int(actual_winner != "Tie")
                bucket["correct"] += int(winner_correct)
                bucket["error"] += margin_error
                bucket["home_wins"] += int(actual_margin > 0)
                bucket["zero_error"] += abs(actual_margin)
                bucket["home3_error"] += abs(actual_margin - Decimal(3))
        elif outcome is not None:
            raise ValueError(f"Pending game has an outcome row: {row['game_id']}")
        population.append(out)

    def summarize(bucket: dict[str, object]) -> dict[str, object]:
        graded = int(bucket["graded"])
        winner_eligible = int(bucket["winner_eligible"])
        result: dict[str, object] = {
            "published_games": int(bucket["published"]),
            "graded_games": graded,
            "pending_games": int(bucket["published"]) - graded,
        }
        if graded:
            divisor = Decimal(graded)
            result.update({
                "winner_correct": int(bucket["correct"]),
                "margin_mae": rounded(bucket["error"] / divisor),
            })
        if winner_eligible:
            result.update({
                "winner_eligible_games": winner_eligible,
                "winner_accuracy": rounded(Decimal(int(bucket["correct"])) / Decimal(winner_eligible)),
            })
        return result

    weekly = {key: summarize(value) for key, value in sorted(stats.items()) if key.startswith("week-")}
    releases = {key: summarize(value) for key, value in sorted(stats.items()) if key.startswith("2026.v")}
    combined = summarize(stats["combined"])
    graded = Decimal(int(stats["combined"]["graded"]))
    winner_eligible = Decimal(int(stats["combined"]["winner_eligible"]))
    baselines = {
        "population": "same graded games as combined CFP Advantage record",
        "home_team_winner": {
            "correct": int(stats["combined"]["home_wins"]),
            "accuracy": rounded(Decimal(int(stats["combined"]["home_wins"])) / winner_eligible),
        },
        "zero_margin": {"margin_mae": rounded(stats["combined"]["zero_error"] / graded)},
        "home_by_3_margin": {"margin_mae": rounded(stats["combined"]["home3_error"] / graded)},
    }
    summary = {
        "schema_version": 1,
        "season": SEASON,
        "record_label": "development validation",
        "combined": combined,
        "by_release": releases,
        "by_week": weekly,
        "same_population_baselines": baselines,
        "definitions": {
            "winner_accuracy": "correct winner grades / graded non-tied games",
            "margin_mae": "mean(abs(actual_margin_home - published_margin_home))",
        },
    }
    population.sort(key=lambda row: (int(row["week"]), row["date"], row["game_id"]))
    return population, summary


def render_population(rows: list[dict[str, str]]) -> bytes:
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=POPULATION_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def render_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-outcomes", type=Path, help="certified team_schedules.csv")
    parser.add_argument("--write", action="store_true", help="write generated replication artifacts")
    args = parser.parse_args()

    rows, receipts, source_paths = load_archive()
    if args.refresh_outcomes:
        refresh_outcomes(args.refresh_outcomes, rows)
    if not (HERE / "outcomes.csv").exists():
        raise ValueError("replication/outcomes.csv is missing")

    population, summary = validate_and_build(rows, receipts)
    source_paths.append(HERE / "outcomes.csv")
    checksums = "".join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in sorted(source_paths))
    manifest = {
        "schema_version": 1,
        "season": SEASON,
        "scope": "canonical designated public receipts; superseded artifacts retained as provenance",
        "hash_normalization": "text line endings normalized to LF",
        "receipts": sorted(receipts, key=lambda item: int(item["week"])),
        "source_file_count": len(source_paths),
        "population_rows": len(population),
        "graded_rows": summary["combined"]["graded_games"],
        "pending_rows": summary["combined"]["pending_games"],
    }
    rendered = {
        "population.csv": render_population(population),
        "summary.json": render_json(summary),
        "manifest.json": render_json(manifest),
        "checksums.sha256": checksums.encode("utf-8"),
    }
    if args.write:
        for name, content in rendered.items():
            (HERE / name).write_bytes(content)
    else:
        drift = [
            name for name in GENERATED
            if not (HERE / name).exists()
            or canonical_bytes((HERE / name).read_bytes()) != canonical_bytes(rendered[name])
        ]
        if drift:
            raise ValueError(f"Generated replication artifacts drifted: {', '.join(drift)}")

    print(
        "PASS: "
        f"{summary['combined']['published_games']} published, "
        f"{summary['combined']['graded_games']} graded, "
        f"{summary['combined']['pending_games']} pending; "
        f"winner accuracy {summary['combined']['winner_accuracy']:.6f}; "
        f"margin MAE {summary['combined']['margin_mae']:.6f}."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, ArithmeticError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
