"""Independently rebuild the aggregate reference tables used for verification.

This script is deliberately separate from the Stata workflow. It accepts the
private, identifier-free analytical CSV, recomputes the study's five reference
tables with pandas and explicit formulas, and writes aggregate outputs only.

It does not create or publish the private analytical file. The input must not
contain review text, Steam identifiers, usernames, or profile information.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT / "stata" / "output" / "tables"

HARMFUL = pd.Timestamp("2024-04-18T20:08:40Z")
FORUM = pd.Timestamp("2024-04-21T22:39:53Z")
DIRECT = pd.Timestamp("2024-04-23T01:54:50Z")
LIVE = pd.Timestamp("2024-04-26T19:39:05Z")
DAY = pd.Timedelta(days=1)
BASELINE = HARMFUL - 14 * DAY
POST_END = LIVE + 14 * DAY

LANGUAGE_NAME = {
    1: "English",
    2: "Simplified Chinese",
    3: "Spanish",
    4: "Japanese",
}

REQUIRED_COLUMNS = {
    "language",
    "created_at",
    "updated_at",
    "created_ms",
    "updated_ms",
    "recommended",
    "eventually_edited",
}

SENSITIVE_COLUMNS = {
    "review",
    "review_text",
    "text",
    "review_id",
    "recommendationid",
    "steamid",
    "steam_id",
    "username",
    "user_name",
    "author",
    "author_id",
    "profile",
    "profile_url",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recompute public-safe aggregate reference tables from the private analytical CSV."
    )
    parser.add_argument("--input", required=True, type=Path, help="Identifier-free private analytical CSV.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory for the five aggregate reference tables.",
    )
    parser.add_argument(
        "--expected-sha256",
        help="Optional expected SHA-256 for the private input; generation stops if it differs.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional manifest path. Defaults to reference_generation_manifest.json beside the tables directory.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_input(path: Path, expected_sha256: str | None) -> tuple[pd.DataFrame, str]:
    if not path.is_file():
        raise SystemExit(f"Private analytical input not found: {path}")

    input_sha256 = sha256(path)
    if expected_sha256 and input_sha256.lower() != expected_sha256.lower():
        raise SystemExit(
            "Input SHA-256 does not match the expected analytical file.\n"
            f"Expected: {expected_sha256.lower()}\nObserved: {input_sha256}"
        )

    data = pd.read_csv(path)
    normalized_columns = {str(column).strip().lower() for column in data.columns}
    sensitive = sorted(normalized_columns & SENSITIVE_COLUMNS)
    if sensitive:
        raise SystemExit(
            "Input rejected because it contains potentially sensitive fields: "
            + ", ".join(sensitive)
        )

    missing = sorted(REQUIRED_COLUMNS - normalized_columns)
    if missing:
        raise SystemExit("Input is missing required analytical fields: " + ", ".join(missing))

    if data.empty:
        raise SystemExit("Input contains no rows.")

    for field in ("language", "recommended", "eventually_edited", "created_ms", "updated_ms"):
        data[field] = pd.to_numeric(data[field], errors="raise")

    if not set(data["language"].unique()).issubset(LANGUAGE_NAME):
        raise SystemExit("Language codes must be a subset of 1=English, 2=Chinese, 3=Spanish, 4=Japanese.")
    if not set(data["recommended"].unique()).issubset({0, 1}):
        raise SystemExit("recommended must contain only 0 and 1.")
    if not set(data["eventually_edited"].unique()).issubset({0, 1}):
        raise SystemExit("eventually_edited must contain only 0 and 1.")

    data["created"] = pd.to_datetime(data["created_at"], utc=True, errors="raise")
    data["updated"] = pd.to_datetime(data["updated_at"], utc=True, errors="raise")
    data["never_edited"] = data["created_ms"] == data["updated_ms"]

    recorded_edit = data["eventually_edited"].astype(bool)
    if not recorded_edit.equals((~data["never_edited"]).astype(bool)):
        raise SystemExit("eventually_edited is inconsistent with created_ms and updated_ms.")
    if (data["updated"] < data["created"]).any():
        raise SystemExit("At least one update timestamp precedes its creation timestamp.")

    return data, input_sha256


def cell(
    frame: pd.DataFrame,
    language: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
    rule: str,
) -> tuple[int, float]:
    keep = (frame["language"] == language) & (frame["created"] >= start) & (frame["created"] < end)
    if rule == "never":
        keep &= frame["never_edited"]
    elif rule == "period_safe":
        keep &= frame["updated"] < end
    elif rule != "final":
        raise ValueError(f"Unknown sample rule: {rule}")

    values = frame.loc[keep, "recommended"]
    if values.empty:
        raise ValueError(f"Empty analytical cell for language={language}, start={start}, end={end}, rule={rule}")
    return int(len(values)), float(values.mean())


def diff_in_gap(
    cells: dict[tuple[str, int], tuple[int, float]],
    control: int,
    after: str,
    before: str,
) -> dict[str, float]:
    estimate = (
        cells[(after, 2)][1]
        - cells[(after, control)][1]
        - cells[(before, 2)][1]
        + cells[(before, control)][1]
    )
    variance = sum(
        rate * (1 - rate) / count
        for period in (after, before)
        for count, rate in (cells[(period, 2)], cells[(period, control)])
    )
    se = math.sqrt(variance)
    z_value = estimate / se
    p_value = math.erfc(abs(z_value) / math.sqrt(2))
    return {
        "estimate": estimate,
        "se": se,
        "ci_low": estimate - 1.96 * se,
        "ci_high": estimate + 1.96 * se,
        "p_value": p_value,
    }


def main_results(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    periods = {
        "baseline": (BASELINE, HARMFUL),
        "disputed": (HARMFUL, LIVE),
        "post": (LIVE, POST_END),
    }
    cell_rows: list[dict[str, object]] = []
    contrast_rows: list[dict[str, object]] = []

    rules = (
        ("never", "Never-edited primary"),
        ("period_safe", "Period-end safeguard"),
        ("final", "Final state naive"),
    )
    controls = ((1, "English"), (3, "Spanish"))
    contrasts = (
        ("Damage vs baseline", "disputed", "baseline"),
        ("Recovery vs disputed", "post", "disputed"),
        ("Post vs baseline", "post", "baseline"),
    )

    for rule, specification in rules:
        for control, control_name in controls:
            cells: dict[tuple[str, int], tuple[int, float]] = {}
            for period, (start, end) in periods.items():
                for language in (2, control):
                    cells[(period, language)] = cell(data, language, start, end, rule)
                    n_reviews, recommend_rate = cells[(period, language)]
                    cell_rows.append(
                        {
                            "specification": specification,
                            "control": control_name,
                            "period": period,
                            "language": LANGUAGE_NAME[language],
                            "n_reviews": n_reviews,
                            "recommend_rate": recommend_rate,
                        }
                    )
            for contrast, after, before in contrasts:
                contrast_rows.append(
                    {
                        "specification": specification,
                        "control": control_name,
                        "contrast": contrast,
                        **diff_in_gap(cells, control, after, before),
                    }
                )

    return pd.DataFrame(cell_rows), pd.DataFrame(contrast_rows)


def local_window(data: pd.DataFrame, cutoff: pd.Timestamp, control: int, days: int = 7) -> dict[str, float]:
    cells: dict[tuple[str, int], tuple[int, float]] = {}
    for period, start, end in (
        ("pre", cutoff - days * DAY, cutoff),
        ("post", cutoff, cutoff + days * DAY),
    ):
        for language in (2, control):
            cells[(period, language)] = cell(data, language, start, end, "never")
    return diff_in_gap(cells, control, "post", "pre")


def placebo_results(data: pd.DataFrame) -> pd.DataFrame:
    dates = list(pd.date_range("2024-03-25", "2024-04-10", tz="UTC"))
    dates += list(pd.date_range("2024-05-05", "2024-05-17", tz="UTC"))
    rows: list[dict[str, object]] = []

    for control, control_name in ((1, "English"), (3, "Spanish")):
        for cutoff in dates:
            rows.append(
                {
                    "control": control_name,
                    "window_type": "placebo",
                    "cutoff": cutoff.date().isoformat(),
                    **local_window(data, cutoff, control),
                }
            )
        for window_type, cutoff in (("focal_harm", HARMFUL), ("focal_repair", LIVE)):
            rows.append(
                {
                    "control": control_name,
                    "window_type": window_type,
                    "cutoff": cutoff.isoformat(),
                    **local_window(data, cutoff, control),
                }
            )
    return pd.DataFrame(rows)


def stage_results(data: pd.DataFrame) -> pd.DataFrame:
    stages = {
        0: ("Baseline", BASELINE, HARMFUL),
        1: ("Patch live", HARMFUL, FORUM),
        2: ("Forum-to-message", FORUM, DIRECT),
        3: ("Message-to-reversion", DIRECT, LIVE),
        4: ("Post-reversion", LIVE, LIVE + 7 * DAY),
    }
    rows: list[dict[str, object]] = []
    for stage, (label, start, end) in stages.items():
        cn_n, cn_rate = cell(data, 2, start, end, "never")
        en_n, en_rate = cell(data, 1, start, end, "never")
        gap = cn_rate - en_rate
        se = math.sqrt(cn_rate * (1 - cn_rate) / cn_n + en_rate * (1 - en_rate) / en_n)
        rows.append(
            {
                "stage": stage,
                "label": label,
                "cn_n": cn_n,
                "cn_rate": cn_rate,
                "en_n": en_n,
                "en_rate": en_rate,
                "gap": gap,
                "ci_low": gap - 1.96 * se,
                "ci_high": gap + 1.96 * se,
            }
        )
    return pd.DataFrame(rows)


def editing_results(data: pd.DataFrame) -> pd.DataFrame:
    event_length = LIVE - HARMFUL
    periods = {
        "Before": (HARMFUL - event_length, HARMFUL),
        "Disputed live": (HARMFUL, LIVE),
        "After reversion": (LIVE, LIVE + event_length),
    }
    rows: list[dict[str, object]] = []
    for period, (start, end) in periods.items():
        for language in (1, 2, 3):
            part = data.loc[
                (data["language"] == language)
                & (data["created"] >= start)
                & (data["created"] < end)
            ]
            rows.append(
                {
                    "period": period,
                    "language": LANGUAGE_NAME[language],
                    "n_reviews": int(len(part)),
                    "n_eventually_edited": int((~part["never_edited"]).sum()),
                    "edit_rate": float((~part["never_edited"]).mean()),
                }
            )
    return pd.DataFrame(rows)


def write_outputs(
    data: pd.DataFrame,
    input_sha256: str,
    output_dir: Path,
    manifest_path: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    period_cells, model_contrasts = main_results(data)
    outputs = {
        "reference_table_01_period_cells.csv": period_cells,
        "reference_table_02_model_contrasts.csv": model_contrasts,
        "reference_table_03_placebo_windows.csv": placebo_results(data),
        "reference_table_04_event_stage_gaps.csv": stage_results(data),
        "reference_table_05_editing_rates.csv": editing_results(data),
    }

    for filename, table in outputs.items():
        table.to_csv(output_dir / filename, index=False)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "input_description": "Private identifier-free Stata analytical CSV",
        "input_rows": int(len(data)),
        "input_sha256": input_sha256,
        "contains_review_text": False,
        "contains_steam_or_profile_identifiers": False,
        "reference_method": "Separate pandas implementation using explicit cell means and difference-in-gap formulas",
        "claim_boundary": "Independent computational reconciliation, not third-party validation or causal identification",
        "tables": {
            filename: {"rows": int(len(table)), "sha256": sha256(output_dir / filename)}
            for filename, table in outputs.items()
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    manifest_path = args.manifest.resolve() if args.manifest else output_dir.parent / "reference_generation_manifest.json"
    data, input_sha256 = load_input(args.input.resolve(), args.expected_sha256)
    write_outputs(data, input_sha256, output_dir, manifest_path)
    print(f"PASS: generated five aggregate reference tables from {len(data):,} privacy-safe rows.")
    print(f"Input SHA-256: {input_sha256}")
    print(f"Tables: {output_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
