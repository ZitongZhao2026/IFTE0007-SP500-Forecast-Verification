# Eva Report v2 — verified empirical evidence handover

This is a research evidence package for revising the English report. It preserves the saved corrected-comparison inputs, supplementary results, methods, and audit records as byte-identical copies. It is **not** a new model run, formal score, final data freeze, or 20 November 2026 forecast. Start with `01_verified_findings/report_ready_findings.md`, then check `CLAIM_TO_EVIDENCE_INDEX.csv` for each report claim and the original calculation file.

## Evidence map and writing scope

| Area | Results | Method and audit | Appropriate use |
|---|---|---|---|
| Original corrected four-model study | `07_methods_and_source_lineage/corrected_comparison/predictions.csv`, `metrics.csv`, `frozen_admission.csv`, `historical_candidate_data.csv` | `rules.json`, `run_comparison.py`, `execution_snapshot.json`, `frozen_training_membership.csv`, `08_independent_review/independent_review.md` | Preserved G3/G4 comparison; the supplementary studies below do not replace it. |
| Paired seven- versus two-factor Ridge | `02_paired_ridge_comparison/paired_ridge_analysis.csv`, `paired_ridge_summary.csv`, `paired_ridge_yearly.csv` | `paired_stats_report.md`, `build_paired_yearly.py`, `08_independent_review/independent_read_only_review.md` | Same-origin 257 G3 and 156 G4 APE differences and win counts; HAC(4) is exploratory. |
| Factor signs and descriptions | `03_coefficient_signs/coefficient_refit_by_origin.csv`, `coefficient_sign_stability.csv`; `01_verified_findings/factor_descriptives_recalculated.csv`, `factor_correlations_recalculated.csv` | `03_coefficient_signs/coefficient_sign_method.md`, `07_methods_and_source_lineage/supplementary_methods/empirical_completion.py` | The 413 × 7 coefficient path comes from **new isolated refitting** of frozen training memberships. It was not archived as original fitted coefficients. RET5 and UST3M signs are contrary to the report's working directions. Associations are not causal. |
| Training-update frequency | `04_refit_frequency_sensitivity/metrics.csv`, `weekly_refit_predictions.csv`, `yearly_metrics.csv` | Its `README.md`; `07_methods_and_source_lineage/supplementary_methods/frozen_analysis_config.json`, `empirical_completion.py`, `test_empirical_completion.py`, `test_results.md` | A **new controlled sensitivity experiment**; report as supplementary evidence, not a replacement for original corrected G3/G4 results. |
| Proxy availability timing | `05_availability_timing_sensitivity/scenario_metrics.csv`, `scenario_coverage.csv`, `scenario_predictions.csv`, `scenario_training_manifest.csv`, `scenario_feature_lineage.csv` | `timing_config.json` and `.sha256`, `run_timing_sensitivity.py`, `rebuild_lineage.py`, `test_timing_sensitivity.py`, `README.md` | A **new assumption-based sensitivity experiment**. T+3 scenarios do not prove actual first publication. |
| Tail and rate effects | `06_tail_and_rate_sensitivity/tail_error_diagnostics.csv`, `tail_error_by_origin.csv`, `tail_case_2025_03_28.json`, `rate_sensitivity_arithmetic.csv` | `tail_error_report.md`, `rate_sensitivity_verification.md`, and `frozen_rate_source/` | Tail analysis recalculates from saved forecasts. The 25bp figures are fixed-coefficient local arithmetic, not a refit or a causal policy shock. The original separately timestamped 7 November rate calculation log was not found. |

The claim index records the exact packaged path for each material statement. Legacy PCA/tree/nested-Ridge metrics are packaged under `07_methods_and_source_lineage/legacy_context/` **only as older-timing context**, never as a same-protocol improvement comparison. The draft PDF under `07_methods_and_source_lineage/report_context/` is the reviewed source document, not empirical proof.

## Limits that must appear in the report

- G4 (2023–2025) was previously viewed and is non-independent. Descriptive HAC p-values do not restore independent-test status.
- Historical availability is based on an approved **Proxy PIT** assumption. Strict PIT, actual first release times, historical vintages, and complete actual exchange-session certification remain UNKNOWN.
- The seven-factor Ridge with alpha=1 has human approval for **model design only**. Do not retune it using this package. Final input snapshot remains BLOCKED and final execution NOT APPROVED; this package has no 13 November run or 20 November forecast.
- The source code is copied without alteration and retains original project-relative path assumptions. Restore its original project layout and dependencies for any separately authorized replication. Do not treat extracted scripts as standalone executable evidence.

## External dependencies

- The member submission ZIPs listed in 07_methods_and_source_lineage/corrected_comparison/input_hashes.csv are not copied here; obtain their exact project paths and SHA-256 from that file before full upstream reruns.
- Upstream CRSP/FRED raw downloads and authentic per-observation release/vintage records are not bundled. The included Stage 2C candidate reference price, corrected candidate input, rules and source hashes are the frozen research-level inputs.
- Scripts retain their original project-relative path assumptions; this ZIP is an evidence handover, not a standalone execution environment. Restore the original project layout and dependencies for any authorized replication.

The `FILE_MANIFEST_SHA256.csv` hashes every ZIP member except itself; this avoids self-reference. The top-level ZIP hash is recorded beside the ZIP. The original source manifest is also preserved at `07_methods_and_source_lineage/supplementary_methods/sha256_manifest.csv`.
