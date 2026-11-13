# Original provider-capture provenance

Task: IFTE0007 public submission evidence release. Role: Data Researcher. Review recorded at 2026-11-13T16:41:51.715426+00:00. Scope: local, read-only inspection of three original frozen captures; no downloads, model fitting, coefficient reconstruction or forecast rerun. Verification implementation: direct JSON/CSV parsing, observation-date comparison, and SHA-256 checks; no model code implemented.

Protocol: `0.1.4-draft`; original SHA-256 `b80853fb0fa9135d58cf4e3d0c308bc11e354db6ade78b90dadf51814f71b706`, matched against the original protocol approval entry. Rules P03, P08 and P10 distinguish observation, retrieval, publication and sharing evidence. Current authorization covers filtered publication of evidence, not a new forecast.

The forecast information cutoff is `2026-11-13T12:00:00+00:00`. For all three captures below, retrieval finished before that cutoff. The last observed row/date contained in each frozen response is 12 November 2026. Observation dates alone do not prove first publication; recorded capture completion provides an upper bound on when this response was collected. These fields preserve the original metadata, including its as-captured `pit_admission=NOT_REVIEWED`; later admission decisions are separate evidence.

This is a **public-safe selected-field transcription** of original metadata, not a byte-identical metadata file. The original `raw_path` field is deliberately omitted because it contains a machine-specific absolute path. The project-relative locators below locate originals for authorized review. Original metadata/raw-byte counts and hashes identify those originals, not this public transcription. If a separate sanitized metadata JSON is published, its changed bytes require their own public-manifest hash; never assign the original metadata hash to the sanitized copy. Originals remain unchanged locally. Full provider responses are not reproduced here, and this note grants no data redistribution rights.

## Yahoo Finance S&P 500 Price Index

- Original frozen metadata locator: `research/2026-11-13/final_forecast_execution_20261113/input_freeze_candidate/yahoo_gspc/yahoo_gspc_20261112T230515832090Z.capture.json`.
- Original metadata: **890 bytes**; SHA-256 `54a6b4e3380edb5b503587b45ad1d3535a604ffcd83a5d81755d1b8c10ba3353`.
- Original frozen response locator: `research/2026-11-13/final_forecast_execution_20261113/input_freeze_candidate/yahoo_gspc/yahoo_gspc_20261112T230515832090Z.json`.
- Original response: **4395 bytes**; SHA-256 `0326b5e3cf85e472f5b4583478c9fec0f0334c29b59c42ed391166ab2ad24ca6`.
- `requested_url`: `https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=1790812800&period2=1794614400&interval=1d&events=history`.
- `response_url`: `https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=1790812800&period2=1794614400&interval=1d&events=history`.
- `retrieval_started_utc`: `2026-11-12T23:05:15.832090+00:00`.
- `retrieval_finished_utc`: `2026-11-12T23:05:15.920322+00:00`.
- `http_status`: `200`.
- `response_date_header`: `EMPTY (not supplied)`.
- `last_modified_header`: `EMPTY (not supplied)`.
- `historical_first_available_at`: `UNKNOWN`.
- Last contained usable observation date before the cutoff: **2026-11-12**. Daily Close `7592.39990234375` raw index points, rounded to **7,592.40** for the recorded P0.

## Cboe VIX

- Original frozen metadata locator: `research/2026-11-13/final_forecast_execution_20261113/input_freeze_candidate/cboe_vix/cboe_vix_20261113T094437810497Z.capture.json`.
- Original metadata: **872 bytes**; SHA-256 `b811a7d02a130e7399d0ea1da2ce18440fb0f5ab5c3fe75e753e115eaafbb19b`.
- Original frozen response locator: `research/2026-11-13/final_forecast_execution_20261113/input_freeze_candidate/cboe_vix/cboe_vix_20261113T094437810497Z.csv`.
- Original response: **474808 bytes**; SHA-256 `2a21208b9e9f61ad60e4d6b028bb9afc85483e4b0b94b69d2f0b1922dfd96820`.
- `requested_url`: `https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv`.
- `response_url`: `https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv`.
- `retrieval_started_utc`: `2026-11-13T09:44:37.810497+00:00`.
- `retrieval_finished_utc`: `2026-11-13T09:44:38.033129+00:00`.
- `http_status`: `200`.
- `response_date_header`: `Fri, 13 Nov 2026 09:44:38 GMT`.
- `last_modified_header`: `Fri, 13 Nov 2026 02:21:03 GMT`.
- `historical_first_available_at`: `UNKNOWN`.
- Last contained usable observation date before the cutoff: **2026-11-12**. CLOSE `18.700000`, matching saved final VIX **18.7**.

## US Treasury daily par yield curve

- Original frozen metadata locator: `research/2026-11-13/final_forecast_execution_20261113/input_freeze_candidate/treasury_curve/treasury_2026_20261113T094334254685Z.capture.json`.
- Original metadata: **1090 bytes**; SHA-256 `c227e5d54218ff0906f5570dcb4018cb333ab3469ad4e0ba73d71aba3aba4a40`.
- Original frozen response locator: `research/2026-11-13/final_forecast_execution_20261113/input_freeze_candidate/treasury_curve/treasury_2026_20261113T094334254685Z.csv`.
- Original response: **17687 bytes**; SHA-256 `83e7b79d584f8f966eaf2239f53b909319437b8aec0c590c429ef161ce7d136f`.
- `requested_url`: `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all?_format=csv&field_tdr_date_value=2026&page=&type=daily_treasury_yield_curve`.
- `response_url`: `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all?_format=csv&field_tdr_date_value=2026&page=&type=daily_treasury_yield_curve`.
- `retrieval_started_utc`: `2026-11-13T09:43:34.254685+00:00`.
- `retrieval_finished_utc`: `2026-11-13T09:43:34.595604+00:00`.
- `http_status`: `200`.
- `response_date_header`: `Fri, 13 Nov 2026 09:43:34 GMT`.
- `last_modified_header`: `EMPTY (not supplied)`.
- `historical_first_available_at`: `UNKNOWN`.
- Last contained usable observation date before the cutoff: **2026-11-12**. 10 Yr **5.10%**, 3 Mo **4.32%**, 2 Yr **4.86%**; 10Y-minus-2Y spread **0.24 percentage points**.

## Results and limits

- **PASS:** original response hashes and byte counts match adjacent metadata for all three providers; capture completion precedes the cutoff; latest recorded observations agree with the saved P0, VIX and Treasury inputs.
- **UNKNOWN:** first publication and historical per-observation availability/vintage. Cboe's `Last-Modified` header is preserved as a header value and is **not** verified publication time. HTTP `Date` is also not first publication. Empty Yahoo/Treasury headers are not filled with inferred values.
- **UNKNOWN:** historical Strict PIT certification remains unchanged. This source check does not certify all historical inputs or prove an independent pre-cutoff second-source check of the Yahoo P0.
- **NOT APPLICABLE:** a new forecast, historical backtest or fitted-coefficient reconstruction; none is needed for this provenance transcription and none was performed.
