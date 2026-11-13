# Paired Ridge errors and serial-correlation-aware uncertainty

`paired_ridge_analysis.csv` joins original saved seven-factor (`MYSELF`) and two-factor (`DMC`) predictions by frozen `forecast_origin_id`, with candidate target close and P0 from the corrected historical row. The output includes each model's level absolute error, APE, and the signed seven-minus-two APE difference. `paired_ridge_yearly.csv` gives year-specific matched comparisons; no date was selected by error.

| Period | n | Seven wins | Two wins | Mean seven-minus-two APE (pp) | Median (pp) | HAC(4) 95% normal-approx interval (pp) |
|---|---:|---:|---:|---:|---:|---:|
| G3 2018–2022 | 257 | 127 | 130 | +0.0237 | +0.0030 | −0.0441 to +0.0915 |
| G4 2023–2025 | 156 | 91 | 65 | −0.0872 | −0.1649 | −0.1675 to −0.0068 |

The HAC estimator uses a fixed four-lag Bartlett kernel on the ordered weekly loss-difference series. This covers short-range serial correlation from overlapping forecast horizons more appropriately than an iid t-test; four lags are a sensitivity convention, not an estimated dependence horizon. The G4 normal-approximation p-value is about 0.034, but **G4 was already examined in development**, the model comparison was selected in that context, historical first availability is unverified, and the p-value is not a confirmatory independent-test result. G3's corresponding value is about 0.493. Neither interval establishes that the models are equivalent or that one is prospectively superior.

The largest five absolute weekly differences contribute signed sums of +1.3577 pp (G3) and −1.1849 pp (G4) to total signed differences of +6.0922 and −13.5975 pp respectively. The complete origins are in `paired_ridge_summary.csv`. These concentrated effects and differing annual signs caution against a single pooled claim.
