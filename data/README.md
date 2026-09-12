# Data boundary and expected schema

Raw Steam review data are not included in this repository. The collection route, confirmed retrieval date, input counts, integrity hashes, and release boundary are documented in `../PROVENANCE.md`. The researcher still needs to review applicable platform terms before any public release.

## Minimum analytical schema

The current intraday module expects a gzip-compressed CSV with these fields:

| Field | Type | Description |
|---|---|---|
| `language` | string | Steam language label; current module uses `schinese` and `english`. |
| `created_at` | UTC timestamp | Original review creation time. |
| `updated_at` | UTC timestamp | Last review update time; equality with `created_at` identifies never-edited reviews. |
| `recommended` | boolean or 0/1 | Steam recommendation vote. |

## Public-release plan

1. Use the committed synthetic dataset in `../stata/data/synthetic/` for public workflow tests; it contains no user-generated text or identifiers.
2. Run the schema and event-window smoke tests in Stata 16 and retain only safe aggregate outputs.
3. Provide retrieval instructions only if the data source permits them.
4. Keep review text and user identifiers out of the repository unless a documented research and licensing basis permits release.

Public-safe aggregate evidence supporting the stated findings is stored in `../evidence/`.
