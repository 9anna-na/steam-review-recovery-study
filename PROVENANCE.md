# Data provenance and public-release boundary

## Case and source

- Product: *Stardew Valley*.
- Steam application ID: `413150`.
- Review endpoint used by the local collector: `https://store.steampowered.com/appreviews/413150`.
- Official event source retained in the case registry: `https://store.steampowered.com/news/posts/?appgroupname=Stardew+Valley&appids=413150&enddate=1730743075&feed=steam_community_announcements`.
- Review creation-time coverage in the analytical source: 2024-03-15 00:08:38 through 2024-05-24 23:56:34 UTC.

## Collection procedure

The retained local collection script is configured to request cursor-paginated Steam review batches with `json=1`, `purchase_type=all`, `num_per_page=100`, and `filter=recent`. Each language is requested separately. The script stores each returned review as one JSON line and saves the next cursor after every batch so that an interrupted download can resume.

The five retained state files confirm that cursor pagination completed 234 English batches, 114 Simplified Chinese batches, 28 Spanish batches, five Latin American Spanish batches, and one Japanese batch. The exact command line used to launch the collection was not preserved, so any additional date or stopping option cannot be reconstructed with certainty.

The five retained raw language files contain:

| Steam language label | Rows |
|---|---:|
| `english` | 23,372 |
| `schinese` | 11,384 |
| `spanish` | 2,793 |
| `latam` | 452 |
| `japanese` | 55 |
| **Total** | **38,056** |

All five raw files and all five associated pagination-state files were created and last modified on 2026-08-23 according to filesystem metadata. Their tightly grouped timestamps support 2026-08-23 as the retrieval date, and the researcher confirmed that this was the original download rather than a later folder copy.

## Integrity record

The raw files remain private. Their SHA-256 digests are recorded so the researcher can verify that later analyses use the same local inputs.

| Private local artifact | SHA-256 |
|---|---|
| English JSONL | `653ff388ec1868509ea5a0199287ed85374583f3f821a9a9851eb18492f8048a` |
| Simplified Chinese JSONL | `5547579b7a268affb79be5a22827dc2bdc1f9e3e9bc5a92e5672534f5c97f4f8` |
| Spanish JSONL | `bb91559c2b4074d325ebf23d4c24c4a0b34780bece232ebb322c93d5145e9e59` |
| Latin American Spanish JSONL | `7b652dbc8c8178c6509e39b65d8828713e29aaf358d1fc8b130d7ea94e4b0ba7` |
| Japanese JSONL | `2dbaf0604b6e5806a5098c4d5116d44c0d95d4e604ca76dfdd9f1acd71dbc5b1` |
| Processed review-level gzip CSV | `97a1bb3888281a608580b4d9f703b1654ea0326cdcf4001467842881f3ab7208` |
| Private Stata analytical CSV | `00e56bb7d3060dd8b5fbbcfda9acb3900f3a6226f02feaa4f4676671324ae7db` |

## Transformation to the analytical file

The private review-level file contains one unique review per row. The processing workflow:

1. parses Steam creation and last-update timestamps as UTC;
2. assigns the Steam language requested during collection;
3. converts the recommendation flag to a binary outcome;
4. converts playtime at review from minutes to hours;
5. removes duplicate review IDs before analysis;
6. derives event periods from exact UTC timestamps; and
7. creates a Stata input that removes review text and Steam identifiers.

The private Stata input contains 38,056 rows and these analytical fields: anonymous row number, language code and label, review date, creation time, last-update time, Stata millisecond timestamps, recommendation outcome, eventual-edit indicator, and playtime hours.

## Measurement limits

Steam exposes the current recommendation state, current text, creation time, and most recent update time. It does not expose the full edit history. A retrospective download can therefore contain revisions made after the original posting date. The preferred historical analysis restricts the sample to reviews whose creation and last-update timestamps are equal. This avoids future revisions leaking into earlier event stages, but changes the target population to reviewers who never edited their reviews.

The data also cover people who chose to post a Steam review. They do not represent all players, and the language comparison is descriptive rather than a causal difference-in-differences design.

## Public-release decision

Raw JSONL files, review text, review IDs, usernames, profile identifiers, and the private analytical CSV are not distributed. The repository contains code, a deterministic synthetic fixture, licensed Stata logs, figures, and aggregate tables only. This boundary protects user-generated content and prevents the synthetic outputs from being confused with substantive research evidence.

## Before publication

- [x] Researcher confirmed that the raw directory was collected in place on 2026-08-23.
- [x] Retained collector defaults and cursor-state batch counts documented; exact launch flags are explicitly recorded as unavailable.
- [ ] Event timestamps and official links receive a final citation check.
- [ ] Redistribution terms are reviewed again before any change to repository visibility.
