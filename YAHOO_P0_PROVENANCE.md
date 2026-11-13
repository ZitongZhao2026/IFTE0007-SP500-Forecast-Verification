# Yahoo Finance P0 source provenance

This note records provenance for the frozen Live P0 used in the approved IFTE0007 forecast. It was prepared from the original archived Yahoo capture and its adjacent capture metadata; no replacement data was fetched.

| Field | Recorded value |
|---|---|
| Exact source URL | `https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=1790812800&period2=1794614400&interval=1d&events=history` |
| Retrieval started | `2026-11-12T23:05:15.832090+00:00` (UTC) |
| Retrieval completed | `2026-11-12T23:05:15.920322+00:00` (UTC) |
| HTTP status | `200` |
| Publication / historical first-availability timestamp | **UNKNOWN**. Capture metadata records `historical_first_available_at=UNKNOWN`; response Date and Last-Modified headers are empty. Retrieval time proves when this archived response was collected, not when Yahoo first published the observation. |
| Last admissible observation date | `2026-11-12` (America/New_York observation date in the Yahoo chart response) |
| Recorded P0 | **7,592.40 index points** (`^GSPC` daily Close). The raw JSON numeric value is `7592.39990234375`, which is recorded to two decimal places as 7,592.40. |
| Original raw capture | `research/2026-11-12/final_execution_prep/yahoo_capture/yahoo_gspc_20261112T230515832090Z.json` |
| Original capture SHA-256 | `0326b5e3cf85e472f5b4583478c9fec0f0334c29b59c42ed391166ab2ad24ca6` |
| Adjacent capture metadata SHA-256 | `54a6b4e3380edb5b503587b45ad1d3535a604ffcd83a5d81755d1b8c10ba3353` |
| Forecast information cutoff | **2026-11-13 12:00 GMT** (`2026-11-13T12:00:00+00:00`) |

The original response URL equals the requested URL in the capture metadata. The archived retrieval completed before the stated forecast information cutoff. This note records that evidence and does not claim the Yahoo historical publication time is known or independently establish Strict PIT.
