# IFTE0007 S&P 500 final forecast — public saved-result verification repository

This repository documents a forecast made with the information cutoff **2026-11-13 12:00 GMT** for the **2026-11-20 S&P 500 Price Index close**. The saved forecast is **7,552.46** index points from P0 **7,592.40** (Yahoo Finance `^GSPC` Close observed 2026-11-12) and a cumulative simple return of **−0.526004%**. The approved design was seven-factor Ridge (α=1), training-only StandardScaler and expanding corrected-proxy training, with 869 mature training rows. The target actual close was not known at forecast time. Strict PIT remains UNKNOWN; this repository does not establish formal scoring eligibility.

## Verify the saved result

Use Python 3 with no third-party packages:

```sh
python3 -I verify_saved_result.py
```

This checks every hash listed in `PUBLIC_FILE_HASHES.csv`, the saved configuration, training count and P0 × (1 + predicted return) conversion. It **does not** independently reproduce the 869-row fit or prove historical first availability. The original result JSON in `result/` and execution code in `code/` are unmodified copies. `result/public_forecast_facts.json` is a clearly marked derived public index to values and private manifest hashes.

Windows: the repository includes `.gitattributes` with `* -text` to preserve the exact audited bytes even when `core.autocrlf=true`. Do not re-save files with an editor that changes line endings before running the hash check. See `CONFIG_SCOPE.md` for the G3 annual-cap wording in the archived research rules, `FINAL_CALCULATION_VERIFICATION.md` for the absent original fitted parameters, and `audit/TRAINING_ORIGIN_COVERAGE.md` for the five excluded Fridays within the 869-row training span.

## Full model rerun

The public package omits historical daily licensed/third-party observations, the training X–Y matrix, Live raw captures, the full execution manifest and the single-use approval record. Consequently **a clean checkout cannot rebuild the training set or refit the forecast**. The archived `code/run_forecast_bound.py` expects the original project layout, source files, governance records and a fresh, separately approved dual-hash single-run authorization. Do not run it from this public checkout, reuse a consumed approval or treat the saved-output check as a full rerun. An authorised holder can obtain sources as described in `DATA_SOURCES_AND_USAGE.md`, reconstruct and audit inputs locally, and follow the private controlled execution workflow; an independent public rerun may not reproduce the same historical data versions.

## Audit trail and limits

`audit/first_attempt_failure_record.md` records an initial approved run that failed after in-memory fitting, before writing a forecast. `audit/final_run_report.md` and `audit/independent_read_only_review.md` document the separately approved, hash-bound retry that produced the saved result. `AUDIT_AND_REPRODUCTION_SCOPE.md` identifies the private manifest hashes and what this public repository can and cannot verify. `config/rules.json` is an earlier corrected-proxy research rule snapshot with `PRECHECK_ONLY` status; it is **not** a reusable final-execution approval.

The three original Chinese audit notes remain in `audit/`; `audit/ENGLISH_AUDIT_SUMMARIES.md` provides faithful English summaries for readers of the coursework report. The separate evidence ZIP contains these records and the saved result without requiring a GitHub link.
