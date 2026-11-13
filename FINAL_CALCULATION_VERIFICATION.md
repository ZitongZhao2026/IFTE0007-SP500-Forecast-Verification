# Final calculation verification and its limit

The successful run saved the seven raw Live feature values in its result JSON and their order in the model config. The P0 value is in the private Live snapshot and derived public facts file; the result JSON saves its observation date, full-precision predicted return and predicted index level. The final-run code fitted a `Pipeline` in memory and returned only the predicted return, predicted level and status fields. A deterministic inventory of all **114 files in the isolated original final-execution directory**, including its result JSON, execution manifest, snapshots and archived ZIP, found **no saved** `Ridge.coef_`, `Ridge.intercept_`, `StandardScaler.mean_`, `StandardScaler.scale_` or serialized fitted model. These original fitted parameters are **unavailable from the archived successful-run artifacts**, not merely absent from the public repository. This does not claim that every possible unarchived backup outside that directory was searched. A later refit could estimate new parameters, but could not be presented as a replay of parameters preserved by the original execution. This package does not refit, infer or invent them.

| Check | Saved evidence | Result |
|---|---|---|
| Model/order | `SEVEN_FACTOR_RIDGE`: RET5, RET20, RV20, VIX, UST10Y, UST3M, SPREAD; α=1 | PASS against archived config/code |
| Raw Live inputs | `0.03245563815913832`, `−0.0195840424790098`, `0.013976687254532893`, `18.7`, `5.1`, `4.32`, `0.23999999999999932` | PASS against saved result and private Live snapshot |
| P0 | Yahoo `^GSPC` Close 7,592.40, observed 2026-11-12 | PASS against private Live snapshot |
| Saved model return | `−0.005260040020305717` cumulative simple return | SAVED OUTPUT; coefficient-level replay unavailable |
| Point conversion | Decimal arithmetic gives `7,552.46367214983087424920`; the saved binary-float output is `7,552.463672149831` | PASS within floating-point precision; two-decimal display 7,552.46 |
| Training membership | 869 unique IDs, 2010-02-05 through 2026-10-30 | PASS against private membership record; matrix excluded from public package |

The deterministic `python3 -I verify_saved_result.py` checks the published file hashes, config/result fields and arithmetic. The private membership matrix and source captures remain controlled audit inputs. The public numerical summary supports **saved-result verification**, not independent re-estimation of the model. Strict PIT remains UNKNOWN.
