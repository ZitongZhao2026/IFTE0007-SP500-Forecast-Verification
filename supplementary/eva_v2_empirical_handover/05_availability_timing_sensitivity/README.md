# Source-specific proxy-delay sensitivity

The frozen corrected rule in `rules.json`, `prepare_no_fit.py` and `run_comparison.py` is: price close available at the next New York natural day 00:00; VIX and each Treasury maturity at observation date +2 New York natural days 23:59:59. The alternative scenarios were hashed **before their predictions were computed** in `timing_config.json`:

1. VIX alone: +3 instead of +2 New York natural days at 23:59:59.
2. Treasury 10Y, 3M and 2Y together (including derived 10Y−2Y spread): +3 instead of +2; VIX unchanged.

Price/P0, target date/level, label proxy maturity, frozen model methods and per-model G3 annual/G4 weekly training conventions are unchanged. The script reloads raw VIX/Treasury CSV, reselects observations under each alternative cutoff, recomputes available-at in `America/New_York` (including DST), checks source-specific staleness and known later missing source records, rebuilds each model's historical training membership, and refits. `scenario_feature_lineage.csv` preserves changed source observation dates and proxy clocks. `scenario_coverage.csv` retains every one of the 417 G3/G4 candidate origins; the four 2019 price-conflict windows remain excluded. `scenario_training_manifest.csv` gives model-specific training hashes and latest proxy-matured label; outputs are assumption-based diagnostics only.

| Scenario | G3 common (base 257) | G4 common (base 156) | Same-origin seven-factor MAPE % / saved base % | Same-origin two-factor MAPE % / saved base % |
|---|---:|---:|---|---|
| VIX +1 additional day | 237 | 153 | G3 2.0442 / 2.0546; G4 1.5261 / 1.5301 | G3 2.0256 / 2.0234; G4 1.6349 / 1.6167 |
| Treasury +1 additional day | 226 | 136 | G3 2.0423 / 2.0516; G4 1.5567 / 1.5596 | G3 2.0193 / 2.0147; G4 1.6310 / 1.6119 |

The changed **factor observation anchors** and stricter staleness/eligibility reduce coverage; the price P0 anchor does not change. The paired numbers above use the **intersection of each scenario's eligible IDs and the original common set**, so they isolate forecast changes on the same evaluation dates; they do not equate a reduced-sample MAPE with the original 257/156 full-sample MAPE. Univariate models whose source is unchanged give identical forecasts on the retained intersection. These are counterfactual delay assumptions, not evidence of any actual historical first-publication time or vintage. Strict PIT remains UNKNOWN; G4 remains previously exposed and non-independent.
