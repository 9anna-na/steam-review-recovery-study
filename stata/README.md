# Stata workflow

The formal analysis was executed in licensed Stata 16.1 on 10 September 2026 using a private 38,056-row analytical file. The repository includes only safe aggregate tables, figures, and a sanitized log from that run.

## Public synthetic run

From this directory, run:

```stata
do analysis.do 1
```

This reads `data/synthetic/steam_reviews_synthetic.csv` and writes artificial test results under `output/synthetic/`. Synthetic estimates demonstrate execution only and are not research findings.

## Private formal run

The formal workflow expects a local file at `data/private/steam_reviews.csv`:

```stata
do analysis.do 0
```

That private file is excluded by `.gitignore` and must not be committed.

## Numerical verification

Researchers with the private analytical CSV can first rebuild the aggregate reference tables through a separate pandas implementation. From the repository root, run:

```bash
python3 src/build_reference_tables.py \
  --input stata/data/private/steam_reviews.csv \
  --output-dir stata/output/tables \
  --expected-sha256 00e56bb7d3060dd8b5fbbcfda9acb3900f3a6226f02feaa4f4676671324ae7db
```

The input is not published. It contains analytical variables but no review text or Steam identifiers, and the generator refuses common sensitive fields. Then run:

```bash
python3 stata/check_stata_results.py
```

The checker compares the formal licensed outputs with the independently computed references. Directly comparable period cells, model contrasts, event stages, 60 stable-period placebo windows, and editing rates pass the recorded tolerances. “Independent” here means a separate pandas implementation, not third-party validation of the private source data.

## Interpretation

The language-by-period specifications are descriptive comparisons, not causal difference-in-differences estimates. Parallel counterfactual trends are not established. The final recommendation state of an edited review can contain information added after its original creation date, which motivates the never-edited specification and its accompanying limitation.
