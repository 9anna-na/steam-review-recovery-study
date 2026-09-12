# Public-safe evidence map

These files support the three descriptive findings stated in the project README without exposing review text or identifiers.

| README finding | Supporting file |
|---|---|
| The recommendation gap narrowed before the direct developer message and approached zero before the live reversion. | `intraday/direct_message_24h_windows.csv` and `intraday/forum_confirmation_24h_windows.csv` |
| Positive Simplified Chinese arrivals increased and negative arrivals decreased between the forum-confirmation and direct-message stages. | `intraday/stage_review_arrivals.csv` and `intraday/stage_arrival_rate_ratios.csv` |
| Sixteen of 28 recommendation-positive audited comments still criticized localization. | `text_audit/text_audit_summary.csv` and `text_audit/CODEBOOK.md` |

The intraday files use never-edited reviews only. The text audit is a single-coder, keyword-enriched, fixed-allocation sample of 40 Simplified Chinese reviews: ten from each event stage. It tests whether concepts can coexist within comments. It must not be used to estimate their prevalence among all Steam reviews.
