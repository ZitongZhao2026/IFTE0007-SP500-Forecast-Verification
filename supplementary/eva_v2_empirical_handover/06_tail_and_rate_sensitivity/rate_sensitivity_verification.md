# 25bp fixed-coefficient rate sensitivity

The `F20261030` retrospective, post-hoc seven-factor snapshot in `research/2026-11-06/nov6_preclose_forecast/frozen_snapshot/frozen_predictions.csv` stores P0 = 7720.39, seven standardized Ridge coefficients and training `StandardScaler` scales. The saved source itself reports simulation cutoff 2026-10-30 12:00 UTC but actual generation 2026-11-06 12:49 UTC, so it is not evidence of a contemporaneously frozen 30 October forecast.

The exact local calculation is `Δpredicted_price = P0 × Σ_j (standardized_coefficient_j / scaler_scale_j) × Δfeature_j`, holding intercept, all other inputs, scales and coefficients fixed. Treasury yields are stored in percent, so +25 basis points is **+0.25** in each yield column, not +0.0025.

| Scenario | Feature changes | Δforecast return | Δforecast level |
|---|---|---:|---:|
| 10Y only +25bp | UST10Y +0.25; 10Y−2Y spread +0.25 | +0.000153077504 | **+1.1818 S&P 500 index points** |
| 3M, 2Y, 10Y parallel +25bp | UST3M +0.25; UST10Y +0.25; spread unchanged | −0.000226646577 | **−1.7498 S&P 500 index points** |

`rate_sensitivity_arithmetic.csv` independently reconstructs these from the frozen parameters and agrees with the saved 8 November recalculation to 1e-10 points. The 8 November script and output exist in `research/2026-11-09/report_author_handover/06_sensitivity_and_failure_analysis/`; a separate timestamped log of the originally claimed 7 November arithmetic run was not found. Report this as a **local fixed-coefficient perturbation**, never a policy shock, refitted-model robustness test or final-forecast sensitivity.
