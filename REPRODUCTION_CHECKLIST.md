# Reproduction checklist

1. Run `python3 -I verify_saved_result.py` from the repository root. Expect `PASS` and `forecast=7552.46`.
2. Inspect `result/final_forecast_result.json`: model `SEVEN_FACTOR_RIDGE`, α=1, seven named factors, training count 869, cutoff 2026-11-13 12:00 UTC, target 2026-11-20.
3. Check P0=7,592.40 in `result/public_forecast_facts.json` against the private reviewed Live snapshot; verify `7592.40 × (1 − 0.005260040020305717) = 7552.463672149831`, rounded to 7,552.46.
4. Compare the result's training manifest, Live bundle and execution manifest SHA-256 with `result/public_forecast_facts.json`. The manifest contents and raw observations remain private; public hashes only prove identity if an authorised reviewer already has those files.
5. Read `audit/first_attempt_failure_record.md`, `audit/final_run_report.md` and `audit/independent_read_only_review.md` together. The first attempt produced no forecast; the second had a new single-use, double-hash approval.
6. Treat the saved-output check as **available** in this repository. Rebuilding training X–Y and refitting the model are **unavailable from this repository alone** because source observations, the frozen training matrix and Live captures are excluded. Strict PIT is UNKNOWN.
