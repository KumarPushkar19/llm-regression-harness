# LLM Output Regression Harness

A small, deterministic test suite for LLM outputs, built with Python and pytest.

**The problem it solves:** when a model is updated (v1 → v2), the team needs to know *exactly* which earlier-correct answers broke. Manual re-rating is slow and inconsistent. This harness re-runs the same rule-based checks on every version, so the comparison is reproducible.

## How it works

1. `test_cases.csv` — one row per prompt, with the rules a correct answer must satisfy:
   - `expected_language` — `hindi` or `english` (detected by script: Devanagari vs Latin)
   - `must_contain` — a required fact or keyword; `A|B` means A **or** B
   - `must_not_contain` — banned phrases such as refusals; `A;B` means neither A nor B
   - `max_words` — length limit
2. `model_outputs.csv` — the actual answers from each model version (`v1`, `v2`, ...).
3. `test_llm_outputs.py` — turns every output row into one pytest test and reports pass/fail with the reason.

Adding a new test case or a new model version means adding a CSV row. No code change needed.

## Run it

```
pip install pytest
pytest -v
```

Save an audit record of the run (`report.txt` in this repo is one such run):

```
pytest -v --tb=line > report.txt          # human-readable
pytest -v --junit-xml=report.xml          # machine-readable, for CI / audit trail
```

Test one version only:

```
MODEL_VERSION=v2 pytest -v
```

The GitHub Actions workflow (`.github/workflows/tests.yml`) runs two jobs on every push and keeps each JUnit report as a build artifact:

- **quality-gate-v1** — the version that must pass; a failure here blocks the release.
- **regression-check-v2** — the candidate version; on the sample data it fails 4 of 6 on purpose, so the report shows what a regression looks like. It is informational and does not block the run.

## Sample result (included data)

| Case | v1 | v2 | Why v2 failed |
|------|----|----|---------------|
| TC01 Capital of India | pass | pass | — |
| TC02 Tea recipe (Hindi) | pass | **fail** | answered in English |
| TC03 15% of 200 | pass | **fail** | said 300 instead of 30 |
| TC04 Weekend plan, Hindi only | pass | **fail** | English + "As an AI, I cannot" refusal |
| TC05 Translate "Good morning" | pass | pass | — |
| TC06 Bike safety tip | pass | **fail** | required fact "helmet" missing |

Result: v1 6/6, v2 2/6 → v2 is a regression and should not pass the quality gate.

## What this is and is not

- It is a **deterministic, rule-based** check: same input, same verdict, every run.
- It is **not** a judgement of tone, naturalness or reasoning quality — those still need human evaluation. In practice the two work together: rules catch the cheap, repeatable failures first; human review covers the rest.

## Ideas to extend

- Load outputs live from an API instead of a CSV.
- Add a `severity` column (minor / moderate / major) and fail the gate only on major defects.
- Export the result as JSON for an audit trail.
