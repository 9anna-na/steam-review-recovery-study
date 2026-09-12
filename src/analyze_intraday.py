"""Intraday timing and review-arrival diagnostics for Stardew Valley."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd


HARMFUL = pd.Timestamp("2024-04-18T20:08:40Z")
FORUM = pd.Timestamp("2024-04-21T22:39:53Z")
DIRECT = pd.Timestamp("2024-04-23T01:54:50Z")
LIVE = pd.Timestamp("2024-04-26T19:39:05Z")


def log_rate_ratio(
    after_count: int,
    after_hours: float,
    before_count: int,
    before_hours: float,
) -> tuple[float, float, float]:
    ratio = (after_count / after_hours) / (before_count / before_hours)
    se = math.sqrt(1 / after_count + 1 / before_count)
    return ratio, math.exp(math.log(ratio) - 1.96 * se), math.exp(math.log(ratio) + 1.96 * se)


def recommendation_gap_window(
    data: pd.DataFrame,
    anchor: pd.Timestamp,
    label: str,
    start_hour: float,
    end_hour: float,
) -> dict[str, float | int | str]:
    """Summarize a complete event window and its normal-approximation gap CI."""
    start = anchor + pd.Timedelta(hours=start_hour)
    end = anchor + pd.Timedelta(hours=end_hour)
    row: dict[str, float | int | str] = {
        "window": label,
        "start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "start_hour": start_hour,
        "end_hour": end_hour,
        "mid_hour": (start_hour + end_hour) / 2,
        "duration_hours": end_hour - start_hour,
    }
    for language, prefix in (("schinese", "cn"), ("english", "en")):
        sample = data.loc[
            (data["language"] == language)
            & (data["created_at"] >= start)
            & (data["created_at"] < end)
        ]
        positive = int(sample["recommended"].sum())
        n = len(sample)
        rate = positive / n
        row[f"{prefix}_n"] = n
        row[f"{prefix}_positive"] = positive
        row[f"{prefix}_negative"] = n - positive
        row[f"{prefix}_rate"] = rate
    gap = float(row["cn_rate"]) - float(row["en_rate"])
    variance = (
        float(row["cn_rate"]) * (1 - float(row["cn_rate"])) / int(row["cn_n"])
        + float(row["en_rate"]) * (1 - float(row["en_rate"])) / int(row["en_n"])
    )
    se = math.sqrt(variance)
    row["cn_minus_en_gap"] = gap
    row["ci_low"] = gap - 1.96 * se
    row["ci_high"] = gap + 1.96 * se
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    data = pd.read_csv(args.input, compression="gzip", parse_dates=["created_at", "updated_at"])
    data = data.loc[
        (data["created_at"] == data["updated_at"])
        & data["language"].isin(["schinese", "english"])
    ].copy()

    live_hour = (LIVE - DIRECT).total_seconds() / 3600
    window_specs = [
        ("-72_to_-48h", -72.0, -48.0),
        ("-48_to_-24h", -48.0, -24.0),
        ("-24_to_+0h", -24.0, 0.0),
        ("+0_to_+24h", 0.0, 24.0),
        ("+24_to_+48h", 24.0, 48.0),
        ("+48_to_+72h", 48.0, 72.0),
        ("+72h_to_live", 72.0, live_hour),
        ("live_to_+24h", live_hour, live_hour + 24.0),
    ]
    window_rows = []
    for label, start_hour, end_hour in window_specs:
        start = DIRECT + pd.Timedelta(hours=start_hour)
        end = DIRECT + pd.Timedelta(hours=end_hour)
        row: dict[str, float | int | str] = {
            "window": label,
            "start": start.isoformat(),
            "end_exclusive": end.isoformat(),
            "start_hour": start_hour,
            "end_hour": end_hour,
            "mid_hour": (start_hour + end_hour) / 2,
            "duration_hours": end_hour - start_hour,
        }
        for language, prefix in (("schinese", "cn"), ("english", "en")):
            sample = data.loc[
                (data["language"] == language)
                & (data["created_at"] >= start)
                & (data["created_at"] < end)
            ]
            positive = int(sample["recommended"].sum())
            row[f"{prefix}_n"] = len(sample)
            row[f"{prefix}_positive"] = positive
            row[f"{prefix}_negative"] = len(sample) - positive
            row[f"{prefix}_rate"] = float(sample["recommended"].mean())
        row["cn_minus_en_gap"] = float(row["cn_rate"]) - float(row["en_rate"])
        window_rows.append(row)
    windows = pd.DataFrame(window_rows)

    # Full-day windows centered on the earlier forum confirmation. These
    # isolate the first 24 hours after the forum commitment from the later
    # developer message, while keeping each comparison aligned to the same
    # clock time on adjacent days.
    forum_windows = pd.DataFrame(
        [
            recommendation_gap_window(data, FORUM, "-48_to_-24h", -48.0, -24.0),
            recommendation_gap_window(data, FORUM, "-24_to_+0h", -24.0, 0.0),
            recommendation_gap_window(data, FORUM, "+0_to_+24h", 0.0, 24.0),
            recommendation_gap_window(data, FORUM, "+24_to_+48h", 24.0, 48.0),
        ]
    )

    stage_specs = {
        "harmful_before_public_commitment": (HARMFUL, FORUM),
        "forum_commitment_before_direct_message": (FORUM, DIRECT),
        "direct_message_before_live_reversion": (DIRECT, LIVE),
        "first_7d_after_live_reversion": (LIVE, LIVE + pd.Timedelta(days=7)),
    }
    stage_rows = []
    for stage, (start, end) in stage_specs.items():
        duration = (end - start).total_seconds() / 3600
        row: dict[str, float | int | str] = {
            "stage": stage,
            "duration_hours": duration,
        }
        for language, prefix in (("schinese", "cn"), ("english", "en")):
            sample = data.loc[
                (data["language"] == language)
                & (data["created_at"] >= start)
                & (data["created_at"] < end)
            ]
            positive = int(sample["recommended"].sum())
            negative = len(sample) - positive
            row[f"{prefix}_n"] = len(sample)
            row[f"{prefix}_positive"] = positive
            row[f"{prefix}_negative"] = negative
            row[f"{prefix}_positive_per_hour"] = positive / duration
            row[f"{prefix}_negative_per_hour"] = negative / duration
        row["cn_positive_per_100_en_reviews"] = 100 * int(row["cn_positive"]) / int(row["en_n"])
        row["cn_negative_per_100_en_reviews"] = 100 * int(row["cn_negative"]) / int(row["en_n"])
        stage_rows.append(row)
    stages = pd.DataFrame(stage_rows)

    arrival_long_rows = []
    for row in stages.itertuples():
        for outcome, count in (
            ("positive", int(row.cn_positive)),
            ("negative", int(row.cn_negative)),
        ):
            per_100 = 100 * count / int(row.en_n)
            # Log-scale Poisson interval. Counts are all positive in this case.
            half_width = 1.96 / math.sqrt(count)
            arrival_long_rows.append(
                {
                    "stage": row.stage,
                    "outcome": outcome,
                    "cn_count": count,
                    "en_review_exposure": int(row.en_n),
                    "cn_reviews_per_100_en_reviews": per_100,
                    "ci_low": per_100 * math.exp(-half_width),
                    "ci_high": per_100 * math.exp(half_width),
                }
            )
    arrival_long = pd.DataFrame(arrival_long_rows)

    indexed = stages.set_index("stage")
    forum_row = indexed.loc["forum_commitment_before_direct_message"]
    direct_row = indexed.loc["direct_message_before_live_reversion"]
    positive_rr = log_rate_ratio(
        int(direct_row.cn_positive), float(direct_row.duration_hours),
        int(forum_row.cn_positive), float(forum_row.duration_hours),
    )
    negative_rr = log_rate_ratio(
        int(direct_row.cn_negative), float(direct_row.duration_hours),
        int(forum_row.cn_negative), float(forum_row.duration_hours),
    )
    rate_ratios = pd.DataFrame(
        [
            {
                "outcome": "chinese_positive_reviews_per_hour",
                "after_vs_before_rate_ratio": positive_rr[0],
                "ci_low": positive_rr[1],
                "ci_high": positive_rr[2],
            },
            {
                "outcome": "chinese_negative_reviews_per_hour",
                "after_vs_before_rate_ratio": negative_rr[0],
                "ci_low": negative_rr[1],
                "ci_high": negative_rr[2],
            },
        ]
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    windows.to_csv(args.output_dir / "direct_message_24h_windows.csv", index=False)
    forum_windows.to_csv(args.output_dir / "forum_confirmation_24h_windows.csv", index=False)
    stages.to_csv(args.output_dir / "stage_review_arrivals.csv", index=False)
    arrival_long.to_csv(args.output_dir / "stage_review_arrivals_long.csv", index=False)
    rate_ratios.to_csv(args.output_dir / "stage_arrival_rate_ratios.csv", index=False)

    win = windows.set_index("window")
    pre_48 = 100 * win.loc["-48_to_-24h", "cn_minus_en_gap"]
    pre_24 = 100 * win.loc["-24_to_+0h", "cn_minus_en_gap"]
    post_24 = 100 * win.loc["+0_to_+24h", "cn_minus_en_gap"]
    lines = [
        "# Intraday timing and review-arrival diagnostic",
        "",
        "This diagnostic uses never-edited reviews only. Twenty-four-hour windows are anchored to the developer's direct Steam message at 2024-04-23 01:54:50 UTC.",
        "",
        "## Was recovery already underway?",
        "",
        f"The Chinese-minus-English recommendation gap was {pre_48:+.2f} pp from 48 to 24 hours before the direct message, {pre_24:+.2f} pp in the final 24 hours before it, and {post_24:+.2f} pp in the first 24 hours after it.",
        "",
        "Recovery had already begun before the direct message, after the forum confirmation started circulating. The direct message coincided with a further improvement, but the full stage contrast cannot be interpreted as the causal effect of message authorship or format.",
        "",
        "## Did positive support enter, or did negative reviewing stop?",
        "",
        f"Between the forum-confirmation stage and the direct-message stage, Chinese positive reviews increased from {forum_row.cn_positive_per_hour:.2f} to {direct_row.cn_positive_per_hour:.2f} per hour (rate ratio {positive_rr[0]:.2f}; 95% CI {positive_rr[1]:.2f} to {positive_rr[2]:.2f}). Chinese negative reviews fell from {forum_row.cn_negative_per_hour:.2f} to {direct_row.cn_negative_per_hour:.2f} per hour (rate ratio {negative_rr[0]:.2f}; 95% CI {negative_rr[1]:.2f} to {negative_rr[2]:.2f}).",
        "",
        f"Normalized to all English reviews, Chinese positive reviews rose from {forum_row.cn_positive_per_100_en_reviews:.1f} to {direct_row.cn_positive_per_100_en_reviews:.1f} per 100 English reviews, while Chinese negative reviews fell from {forum_row.cn_negative_per_100_en_reviews:.1f} to {direct_row.cn_negative_per_100_en_reviews:.1f}.",
        "",
        "The aggregate recovery therefore combines two behaviors: protest de-escalation and an influx of supportive recommendations. Unequal stage duration, daily activity cycles, and endogenous reviewing still prevent a causal interpretation.",
    ]
    (args.output_dir / "intraday_and_volume_findings.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
