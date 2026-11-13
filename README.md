# IFTE0007 — S&P 500 forecast and public submission evidence

**Approved forecast: 7,552.46 index points** for the S&P 500 Price Index close on **20 November 2026**. Information cutoff: **13 November 2026, 12:00 GMT**. Saved P0: **7,592.40** (Yahoo ^GSPC, 12 November); saved simple return: **−0.005260040020305717**. Model: seven-factor Ridge, alpha=1, 869 training observations.

The original [forecast JSON](result/final_forecast_result.json), execution code, model configuration and original audits are unchanged. Forecast JSON SHA-256: `ab11509624c4923e924fb624a305cddaa66a2262728e6c99252110d49b0c627b`.

Start with the [evidence index](EVIDENCE_INDEX.md). It links the report's governance, transcript, historical comparison, supplementary analysis and final-execution evidence. [Provider provenance](PROVIDER_CAPTURE_PROVENANCE.md) records original Yahoo, Treasury and VIX URLs, retrieval timestamps and capture hashes, with publication-time limits. [Public release scope](PUBLIC_RELEASE_SCOPE.md), [publication manifest](PUBLICATION_MANIFEST.csv) and [source-reference map](PUBLIC_REFERENCE_MAP.csv) explain redactions and excluded dependencies.

## Verify without financial downloads or model execution

Download this repository using GitHub's Code → Download ZIP, extract it, open a terminal in its root, and run:

```sh
python3 -I verify_saved_result.py
python3 -I verify_public_evidence.py
```

Both checks use the Python standard library. They verify all published file hashes, the saved result arithmetic and selected aggregate-summary arithmetic. The original saved forecast calculation is 7,592.40 × (1 − 0.005260040020305717) = 7,552.463672149831, rounded to **7,552.46**. Source scripts are provided for inspection; these two verification commands do not import or run forecasting models. Recorded research software versions are in [requirements.txt](requirements.txt), [python_runtime.txt](python_runtime.txt) and the saved [supplementary runtime summary](supplementary/eva_v2_empirical_handover/07_methods_and_source_lineage/supplementary_methods/run_summary.json).

## Reproducibility limits

Original final fitted coefficients, intercept and scaler statistics were not saved. Full training inputs, provider downloads and uncertain row-level derived data are excluded from public redistribution; a full offline retraining is unavailable. Historic model metrics can be inspected as saved aggregate results, but cannot all be regenerated from the public repository. The supplementary calculation and fitting scripts retain original dependency paths and must not be described as standalone rerunnable models. Historical Strict PIT and actual first-publication times remain UNKNOWN; G4 is previously exposed and non-independent. Full role histories and some original execution logs remain missing. The public ledger and provider metadata are explicitly labelled path-redacted projections; original file hashes remain available. See the scope and exclusions for the precise remaining gaps.
