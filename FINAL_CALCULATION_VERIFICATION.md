# Final calculation verification and its limit

The successful run saved the seven raw Live feature values in its result JSON and their order in the model config. The P0 value is in the private Live snapshot and derived public facts file; the result JSON saves its observation date, full-precision predicted return and predicted index level. Its result JSON and execution manifest **did not save** `Ridge.coef_`, `Ridge.intercept_`, `StandardScaler.mean_` or `StandardScaler.scale_`; no fitted-model binary was found in the isolated final-run artifacts. Accordingly, the fitted return **cannot be recomputed from saved coefficients without refitting**. This package does not refit, infer or invent those parameters.

| Check | Saved evidence | Result |
|---|---|---|
| Model/order | `SEVEN_FACTOR_RIDGE`: RET5, RET20, RV20, VIX, UST10Y, UST3M, SPREAD; α=1 | PASS against archived config/code |
| Raw Live inputs | `0.03245563815913832`, `−0.0195840424790098`, `0.013976687254532893`, `18.7`, `5.1`, `4.32`, `0.23999999999999932` | PASS against saved result and private Live snapshot |
| P0 | Yahoo `^GSPC` Close 7,592.40, observed 2026-11-12 | PASS against private Live snapshot |
| Saved model return | `−0.005260040020305717` cumulative simple return | SAVED OUTPUT; coefficient-level replay unavailable |
| Point conversion | Decimal arithmetic gives `7,552.46367214983087424920`; the saved binary-float output is `7,552.463672149831` | PASS within floating-point precision; two-decimal display 7,552.46 |
| Training membership | 869 unique IDs, 2010-02-05 through 2026-10-30 | PASS against private membership record; matrix excluded from public package |

The deterministic `python3 -I verify_saved_result.py` checks the published file hashes, config/result fields and arithmetic. The private membership matrix and source captures remain controlled audit inputs. The public numerical summary supports **saved-result verification**, not independent re-estimation of the model. Strict PIT remains UNKNOWN.
