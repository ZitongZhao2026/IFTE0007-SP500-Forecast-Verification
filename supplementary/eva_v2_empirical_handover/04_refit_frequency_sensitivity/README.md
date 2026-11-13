# Isolated G3 training-update-frequency experiment

The original `run_comparison.py` and `frozen_training_membership.csv` show that seven-factor Ridge, VIX+UST10Y Ridge and UST10Y OLS use a preceding-year-end training-origin ceiling in G3; RV20 OLS already updates at each origin. In G4, all four update at each origin. No reviewed decision record explains *why* the G3 annual ceiling was chosen. It is therefore an implementation convention, not a substantiated pre-specified economic rationale. Model-specific feature gates and minimum samples differ and are retained.

The isolated script `../empirical_completion.py` removes only that G3 annual ceiling. The 257 evaluation IDs, target/P0, original qualifying historical X–Y rows, source proxy clocks, label maturity, model formulas, fixed alpha and within-training-window scaling remain. `weekly_refit_predictions.csv` records each new training count, final training origin, maximum proxy label maturity and training-ID SHA. New fits are marked `SUPPLEMENTARY_EXPLORATORY_REFITTING_SENSITIVITY`; old predictions are read only.

| Model | Original G3 MAPE % | Weekly-update MAPE % | Change (pp) | Mean extra training rows |
|---|---:|---:|---:|---:|
| Seven-factor Ridge | 2.0941 | 2.0913 | −0.0028 | 24.28 |
| VIX+UST10Y Ridge | 2.0704 | 2.0782 | +0.0078 | 24.28 |
| RV20 OLS | 2.0963 | 2.0963 | 0 | 0 |
| UST10Y OLS | 2.0778 | 2.0850 | +0.0072 | 24.28 |

The G3 MAPE order remains VIX+UST10Y Ridge, UST10Y OLS, seven-factor Ridge, RV20 OLS under weekly updating; the two-factor advantage over seven-factor shrinks from 0.0237 to 0.0131 percentage points but does not reverse. Results do not justify revising the approved final model or retroactively overwriting original G3. They show that error levels and pairwise gaps can be sensitive to differing training-update conventions, even where this particular ranking is unchanged.
