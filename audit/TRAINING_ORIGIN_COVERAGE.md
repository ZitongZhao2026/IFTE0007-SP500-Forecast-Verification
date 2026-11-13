# Final training-origin coverage (date and gate metadata only)

The successful run's private `final_forecast_2026-11-20_retry1_training_membership.csv` contains **869 unique** `forecast_origin_id` values, dated 2010-02-05 through 2026-10-30. That inclusive date range contains **874 Fridays**. The companion `ORIGIN_COVERAGE_RECONCILIATION.csv` lists **each of those 874 dates**, its origin ID, included/excluded status and exclusion reason where applicable. The private source paths and SHA-256 values supporting the reconciliation are listed below. A deterministic date-set difference finds the five Fridays below; the original exclusion record gives their pre-existing gate reasons. This is date/gate metadata, not a published copy of the historical training matrix.

| Friday / origin ID | Recorded exclusion reason | Interpretation |
|---|---|---|
| 2012-11-02 / F20121102 | `VALIDATION:VIX exceeds the approved conservative five-calendar-day staleness cap` | A required VIX input failed the fixed recency gate. |
| 2019-08-16 / F20190816 | `SOURCE_BLOCKER:ISOLATED_KNOWN_2019_PRICE_CONFLICT` | Isolated 2019-08-12 price-discrepancy influence window. |
| 2019-08-23 / F20190823 | `SOURCE_BLOCKER:ISOLATED_KNOWN_2019_PRICE_CONFLICT` | Same pre-declared isolation. |
| 2019-08-30 / F20190830 | `SOURCE_BLOCKER:ISOLATED_KNOWN_2019_PRICE_CONFLICT` | Same pre-declared isolation. |
| 2019-09-06 / F20190906 | `SOURCE_BLOCKER:ISOLATED_KNOWN_2019_PRICE_CONFLICT` | Same pre-declared isolation. |

No Friday in this range is missing solely because of a holiday in the checked membership-versus-exclusion comparison. The historical exclusion file includes other exclusions outside this specific inclusive range and is not reproduced here. The 869-row approved training candidate and the successful run's training membership have the same ordered origin IDs. These findings do not change the frozen membership or justify filling the five gaps.

Private evidence paths and SHA-256 values (available to an authorised local reviewer):

- `research/2026-11-13/final_forecast_execution_20261113/final_forecast_2026-11-20_retry1_training_membership.csv` — `a5f248185ec4007606978ca1cee2f6f44047112223254da831f8de507d8638d2`.
- `research/2026-11-06/final_training_data_completion/historical_training_exclusions_v8.csv` — `b4360f01ff39c5c87cd343753c7f3f1b512985ed5814f9362121df6f43788cf4`.

Reconstruction method: enumerate calendar dates from the minimum to maximum membership `forecast_date`, retain `weekday()==4`, subtract the membership dates, and match the five resulting `forecast_origin_id` values to the original exclusion record. This date arithmetic does not infer trading sessions or alter any model input. Historical training remains Corrected Proxy PIT; Strict PIT is UNKNOWN.
