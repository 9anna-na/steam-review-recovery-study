"""Reconcile formal Stata aggregate outputs with separately computed references.

The reference tables can be rebuilt from the private identifier-free analytical
CSV by running src/build_reference_tables.py. This checker does not generate the
references itself and does not authenticate undistributed source data.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
TABLES = HERE / "output" / "tables"
TOLERANCE = 1e-4


def load(name: str) -> pd.DataFrame:
    path = TABLES / name
    if not path.exists():
        raise SystemExit(f"Required table is missing: {path}")
    return pd.read_csv(path)


def require_complete(label: str, merged: pd.DataFrame, actual_n: int, reference_n: int) -> None:
    if len(merged) != actual_n or len(merged) != reference_n:
        raise SystemExit(
            f"FAIL: {label} has unmatched rows "
            f"(actual={actual_n}, reference={reference_n}, matched={len(merged)})."
        )


def finish(label: str, differences: list[float], tolerance: float = TOLERANCE) -> float:
    maximum = float(max(differences, default=0.0))
    if maximum > tolerance:
        raise SystemExit(
            f"FAIL: {label} maximum numeric discrepancy {maximum:.8f} "
            f"exceeds {tolerance:.4f}."
        )
    print(f"PASS  {label:<24} max numeric discrepancy = {maximum:.8f}")
    return maximum


def require_equal(label: str, left: pd.Series, right: pd.Series) -> None:
    if not left.reset_index(drop=True).equals(right.reset_index(drop=True)):
        raise SystemExit(f"FAIL: {label} differs in an exact count field.")


def check_period_cells() -> float:
    actual = load("table_02_period_cells.csv")
    reference = load("reference_table_01_period_cells.csv")
    reference = reference.loc[
        (reference["specification"] == "Never-edited primary")
        & (reference["control"] == "English")
    ].copy()
    reference["period"] = reference["period"].map(
        {
            "baseline": "14-day baseline",
            "disputed": "Disputed localization live",
            "post": "14 days after reversion",
        }
    )
    keys = ["language", "period"]
    merged = actual.merge(reference, on=keys, suffixes=("_actual", "_reference"), validate="one_to_one")
    require_complete("period cells", merged, len(actual), len(reference))
    require_equal("period cells", merged["n_reviews_actual"], merged["n_reviews_reference"])
    return finish(
        "period cells",
        [(merged["recommend_rate_actual"] - merged["recommend_rate_reference"]).abs().max()],
    )


def check_model_contrasts() -> float:
    actual = load("table_03_model_contrasts.csv")
    reference = load("reference_table_02_model_contrasts.csv")
    keys = ["specification", "control", "contrast"]
    reference = reference.merge(actual[keys], on=keys, validate="one_to_one")
    merged = actual.merge(reference, on=keys, suffixes=("_actual", "_reference"), validate="one_to_one")
    require_complete("model contrasts", merged, len(actual), len(reference))
    return finish(
        "model contrasts",
        [
            (merged[f"{field}_actual"] - merged[f"{field}_reference"]).abs().max()
            for field in ("estimate", "se", "ci_low", "ci_high")
        ],
    )


def check_event_stages() -> float:
    actual = load("table_06_event_stage_gaps.csv").rename(columns={"stage": "label"})
    reference = load("reference_table_04_event_stage_gaps.csv")
    merged = actual.merge(reference, on="label", suffixes=("_actual", "_reference"), validate="one_to_one")
    require_complete("event stages", merged, len(actual), len(reference))
    require_equal("event stages English N", merged["n0"], merged["en_n"])
    require_equal("event stages Chinese N", merged["n1"], merged["cn_n"])
    field_pairs = (
        ("rate0", "en_rate"),
        ("rate1", "cn_rate"),
        ("gap_actual", "gap_reference"),
        ("ci_low_actual", "ci_low_reference"),
        ("ci_high_actual", "ci_high_reference"),
    )
    # Stata's collapse (semean) uses a finite-sample variance convention,
    # whereas the independent reference uses p(1-p)/n. Counts, rates, and
    # point gaps must match tightly; confidence limits may differ by <0.0003.
    return finish(
        "event stages",
        [(merged[left] - merged[right]).abs().max() for left, right in field_pairs],
        tolerance=3e-4,
    )


def check_placebos() -> float:
    actual = load("table_07_placebo_windows.csv").rename(columns={"cutoff_date": "cutoff"})
    reference = load("reference_table_03_placebo_windows.csv")
    # Compare the 60 stable-period placebos. The four focal rows are excluded:
    # Stata's table uses calendar-day cutoffs, while the reference file uses
    # exact intraday event timestamps, so those rows are not the same estimand.
    actual = actual.loc[actual["window_type"] == "placebo"].copy()
    reference = reference.loc[reference["window_type"] == "placebo"].copy()
    actual["cutoff"] = actual["cutoff"].astype(str).str.slice(0, 10)
    reference["cutoff"] = reference["cutoff"].astype(str).str.slice(0, 10)
    keys = ["control", "window_type", "cutoff"]
    merged = actual.merge(reference, on=keys, suffixes=("_actual", "_reference"), validate="one_to_one")
    require_complete("stable placebo windows", merged, len(actual), len(reference))
    return finish(
        "stable placebo windows",
        [
            (merged[f"{field}_actual"] - merged[f"{field}_reference"]).abs().max()
            for field in ("estimate", "se", "ci_low", "ci_high")
        ],
    )


def check_editing_rates() -> float:
    actual = load("table_08_editing_rates.csv").rename(
        columns={"edit_period": "period", "n_edited": "n_eventually_edited"}
    )
    reference = load("reference_table_05_editing_rates.csv")
    keys = ["period", "language"]
    merged = actual.merge(reference, on=keys, suffixes=("_actual", "_reference"), validate="one_to_one")
    require_complete("editing rates", merged, len(actual), len(reference))
    require_equal("editing rates N", merged["n_reviews_actual"], merged["n_reviews_reference"])
    require_equal(
        "editing rates edited N",
        merged["n_eventually_edited_actual"],
        merged["n_eventually_edited_reference"],
    )
    return finish(
        "editing rates",
        [(merged["edit_rate_actual"] - merged["edit_rate_reference"]).abs().max()],
    )


def main() -> None:
    checks = [
        check_period_cells,
        check_model_contrasts,
        check_event_stages,
        check_placebos,
        check_editing_rates,
    ]
    maxima = [check() for check in checks]
    print(
        "\nPASS: all checked formal Stata aggregate tables agree with "
        f"independent references. Overall maximum discrepancy: {max(maxima):.8f}"
    )


if __name__ == "__main__":
    main()
