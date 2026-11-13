# English summaries of the original Chinese audit notes

These summaries are translations of scope and findings, not replacement audit opinions. The unchanged Chinese originals remain beside this file.

## `first_attempt_failure_record.md`

The first approved, single-use attempt was bound to training manifest `8584a58a1597c9a3398e32cd09a0777442444d68e14379dae7dea482bef24ce4` and Live bundle `17f0da91ccf4f925b5a5f30dc681d51f99cd73bd23fb15e6c2342d0b5ddd826a`. Input checks passed and a model was fitted in memory. Building the execution manifest then failed because the isolated directory lacked `model_candidates.json`. Two partial artifacts were retained, but **no final forecast JSON or execution manifest was written**. The first approval was treated as consumed. The configuration was copied unchanged and a new, separately hash-bound approval was required for a retry.

## `final_run_report.md`

The separately approved retry used seven-factor Ridge (α=1), a training-only StandardScaler and 869 matured corrected-proxy training observations. Its information cutoff was 2026-11-13 12:00 GMT and target was the 2026-11-20 S&P 500 Price Index close. Yahoo `^GSPC` 2026-11-12 Close supplied P0=7,592.40. The saved predicted cumulative simple return was −0.005260040020305717 and the predicted level 7,552.463672149831 (displayed as 7,552.46). The training manifest hash was `5ac4fcd831041a851ac2038e12ddef4b2391245a5e41cebc53b9847ead336a27`; the Live bundle hash was unchanged. The report records `LIVE_INPUTS_CUTOFF_VERIFIED`, `PROXY_HISTORICAL_INPUTS`, `STRICT_PIT_UNKNOWN` and formal scoring `NOT_AUTHORIZED`. The actual target close was not included.

## `independent_read_only_review.md`

An independent read-only reviewer reported PASS for the authorized single Proxy PIT run's artifact integrity. The reviewer checked 17 frozen training files, 46 execution-manifest file hashes, the 869 unique matured training IDs, P0 and price conversion, and preservation of the failed first attempt. The saved pre-cutoff FRED price file had **no 2026-11-12 observation**, so Yahoo's 7,592.40 P0 did not have a second, archived same-date price-source check at the cutoff. The limited Yahoo source approval and NYSE session evidence were recorded; a cited AP link was not retained locally as a separately hash-verifiable same-date source artifact. This did **not** certify Strict PIT. Treasury's true first release and precise session-end time remained UNKNOWN; the target's actual session and close had not yet occurred.

For report wording: describe one failed approved attempt followed by a newly approved retry. Do not imply that the first attempt produced a published forecast or that the retry was a Strict PIT-certified or formally scored result.
