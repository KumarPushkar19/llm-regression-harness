"""
LLM Output Regression Harness
-----------------------------
Runs the SAME deterministic checks on saved outputs from every model version,
so you can see what broke (or got fixed) between v1 and v2.

Files:
  test_cases.csv    -> the rules for each prompt (what a correct answer must look like)
  model_outputs.csv -> the actual answers each model version gave

Run:  pytest -v
Report: pytest -v --tb=short > report.txt
"""

import csv
import re
import pytest

# ---------- 1. Load the data ----------

def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

CASES = {row["case_id"]: row for row in load_csv("test_cases.csv")}
OUTPUTS = load_csv("model_outputs.csv")

# Each row of model_outputs.csv becomes one test. The id shows up in the report,
# e.g.  test_output[TC03-v2]
PARAMS = [
    pytest.param(row, id=f"{row['case_id']}-{row['model_version']}")
    for row in OUTPUTS
]

# ---------- 2. Helper checks (small, readable, deterministic) ----------

DEVANAGARI = re.compile(r"[\u0900-\u097F]")   # Hindi script characters
LATIN = re.compile(r"[A-Za-z]")

def detected_language(text):
    """Very simple rule: whichever script has more characters wins."""
    hindi = len(DEVANAGARI.findall(text))
    english = len(LATIN.findall(text))
    return "hindi" if hindi >= english else "english"

def _has(text, item):
    """A number must match as a whole number ('30' must not match inside '300').
    Words are matched case-insensitively."""
    item = item.strip()
    if item.isdigit():
        return re.search(rf"(?<!\d){re.escape(item)}(?!\d)", text) is not None
    return item.lower() in text.lower()

def contains_any(text, options):
    """'A|B' means the output must contain A OR B. Empty rule = no check."""
    if not options:
        return True
    return any(_has(text, opt) for opt in options.split("|"))

def contains_none(text, banned):
    """'A;B' means the output must NOT contain A and must NOT contain B."""
    if not banned:
        return True
    return not any(b.strip().lower() in text.lower() for b in banned.split(";"))

# ---------- 3. The test ----------

@pytest.mark.parametrize("row", PARAMS)
def test_output(row):
    case = CASES[row["case_id"]]
    out = row["output"]
    failures = []

    # Check A: language
    if case["expected_language"] and detected_language(out) != case["expected_language"]:
        failures.append(f"LANGUAGE: expected {case['expected_language']}, got {detected_language(out)}")

    # Check B: required content (fact / keyword)
    if not contains_any(out, case["must_contain"]):
        failures.append(f"MISSING: output must contain one of '{case['must_contain']}'")

    # Check C: forbidden phrases (refusals, meta-talk)
    if not contains_none(out, case["must_not_contain"]):
        failures.append(f"FORBIDDEN: output contains a banned phrase from '{case['must_not_contain']}'")

    # Check D: length limit
    words = len(out.split())
    if case["max_words"] and words > int(case["max_words"]):
        failures.append(f"LENGTH: {words} words, limit {case['max_words']}")

    assert not failures, f"{row['case_id']} [{row['model_version']}] -> " + " | ".join(failures)
