"""Build a deterministic, public-safe fixture for the Steam Stata workflow.

The rows are entirely synthetic. They reproduce only the schema and broad event
structure needed to exercise imports, date handling, models, placebos, and
figures. They are not Steam reviews and must not be used as research evidence.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "data" / "synthetic" / "steam_reviews_synthetic.csv"
EPOCH = datetime(1960, 1, 1, tzinfo=timezone.utc)
START = datetime(2024, 3, 18, tzinfo=timezone.utc)
END = datetime(2024, 5, 24, tzinfo=timezone.utc)
HARMFUL = datetime(2024, 4, 18, 20, 8, 40, tzinfo=timezone.utc)
FORUM = datetime(2024, 4, 21, 22, 39, 53, tzinfo=timezone.utc)
DIRECT = datetime(2024, 4, 23, 1, 54, 50, tzinfo=timezone.utc)
LIVE = datetime(2024, 4, 26, 19, 39, 5, tzinfo=timezone.utc)

LANGUAGES = {
    1: "English",
    2: "Simplified Chinese",
    3: "Spanish",
    4: "Japanese",
}


def milliseconds(value: datetime) -> int:
    return round((value - EPOCH).total_seconds() * 1000)


def recommendation_rate(language: int, created: datetime) -> float:
    if language != 2:
        return {1: 0.96, 3: 0.95, 4: 0.94}[language]
    if created < HARMFUL:
        return 0.95
    if created < FORUM:
        return 0.74
    if created < DIRECT:
        return 0.70
    if created < LIVE:
        return 0.90
    return 0.96


def edit_rate(language: int, created: datetime) -> float:
    if language == 2 and HARMFUL <= created < LIVE:
        return 0.40
    return {1: 0.05, 2: 0.07, 3: 0.06, 4: 0.05}[language]


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "row_id",
        "language",
        "language_name",
        "review_date",
        "created_at",
        "updated_at",
        "created_ms",
        "updated_ms",
        "recommended",
        "eventually_edited",
        "playtime_hours",
    ]
    rows: list[dict[str, object]] = []
    day = START
    row_id = 1
    while day.date() <= END.date():
        day_index = (day - START).days
        for language, language_name in LANGUAGES.items():
            for position in range(12):
                created = day + timedelta(hours=position * 2, minutes=language * 3)
                recommend_score = (day_index * 19 + position * 31 + language * 17) % 100
                edit_score = (day_index * 23 + position * 29 + language * 13) % 100
                recommended = int(recommend_score < 100 * recommendation_rate(language, created))
                edited = int(edit_score < 100 * edit_rate(language, created))
                updated = created + timedelta(days=1 + (position % 3), hours=language) if edited else created
                rows.append(
                    {
                        "row_id": row_id,
                        "language": language,
                        "language_name": language_name,
                        "review_date": created.strftime("%Y-%m-%d"),
                        "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_at": updated.strftime("%Y-%m-%d %H:%M:%S"),
                        "created_ms": milliseconds(created),
                        "updated_ms": milliseconds(updated),
                        "recommended": recommended,
                        "eventually_edited": edited,
                        "playtime_hours": round(8 + ((day_index * 7 + position * 11 + language * 5) % 500), 1),
                    }
                )
                row_id += 1
        day += timedelta(days=1)

    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows):,} entirely synthetic rows to {OUTPUT}")


if __name__ == "__main__":
    main()
