# Text-audit codebook

## Purpose and sample

The audit checks whether a recommendation-positive vote can coexist with negative localization language and positive evaluation of the developer. It uses 40 Simplified Chinese comments that matched a predefined translation-keyword frame, with ten comments sampled from each event stage.

The coder saw only the comment text and an anonymous code during coding. Recommendation status and event stage were revealed after coding. The audit was completed by one coder. It does not provide inter-rater reliability evidence.

## Binary variables

Each variable equals `1` only when the relevant meaning is stated in the comment. Otherwise it equals `0`. Tone, implication, sarcasm, or presumed motive alone are insufficient.

### `explicit_localization_criticism`

Code `1` when the comment directly evaluates the Chinese translation, terminology, font, localization process, or translation team negatively. General criticism of the game without a localization target is `0`.

### `explicit_positive_developer_or_response_evaluation`

Code `1` when the comment directly praises the developer, the developer's attitude, communication, decision, promised response, or implemented response. A positive Steam recommendation by itself is `0`. Saying only that the translation was restored is also `0` unless the author evaluates that response positively.

### `explicit_rating_or_review_action_discussion`

Code `1` when the comment explicitly refers to giving, keeping, removing, changing, or explaining a Steam review or recommendation. Ordinary praise or criticism without reference to a rating or review action is `0`.

### `explicit_collective_rating_call`

Code `1` only when the author directly asks or instructs other people to leave, remove, or change a review or recommendation. Describing the author's own rating action is `0`. General pressure on the developer without an instruction to other reviewers is also `0`.

## Interpretation limits

- The sample was enriched for localization keywords and fixed at ten comments per stage. Its percentages do not estimate population prevalence.
- The audit can establish coexistence within the sampled comments. It cannot establish why a reviewer selected a positive recommendation.
- The current evidence is single-coder coding. A later independent coder could assess inter-rater reliability, but no such statistic is claimed here.
- Review text and identifiers remain private. The repository publishes only definitions and aggregate counts.
