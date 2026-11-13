# Checks performed before and after supplementary calculations

- Five synthetic unit tests passed: zero/serial-correlation HAC behavior, level error arithmetic, New York winter/summer UTC conversion, and a later known-missing source row blocking a proxy selection.
- Frozen configuration SHA-256 and every declared source hash were checked before fitting. The original corrected runner's input hash list also passed unchanged.
- The corrected frozen admission set contains exactly 257 G3 and 156 G4 common origin IDs. Saved predictions contain 1,652 unique model × origin rows.
- Every one of 413 isolated seven-factor refits used the archived training-ID list and hash and reproduced the saved return within an absolute 1e-10 tolerance before its coefficients were used.
- Frozen-input Table A1/A2 recalculation gives VIX means 21.4796/17.1828 and RV20–VIX correlations 0.862714/0.740976 (G3/G4), agreeing with the PDF after displayed rounding.
- The controlled weekly-update experiment yielded 257 × 4 = 1,028 predictions. RV20 OLS, originally weekly, retained identical member IDs and predictions for all 257 origins.
- The two one-source-at-a-time availability-delay scenarios retained 237+153 and 226+136 origins respectively. Their full 417-origin coverage tables and 3,008 total model predictions are saved independently of the frozen source study.
- The 2,085-row scenario feature lineage was recreated independently with `availability_timing_sensitivity/rebuild_lineage.py`; both CSVs have SHA-256 `7715ff7803d923c22bfbd2cedda8ef65671f3dd8bcf16f83b392ef55e627078f`.
- No actual historical first-publication timestamp or complete actual-session calendar was certified. These checks do not authorize Formal scoring, Strict PIT or the final forecast.
- `sha256_manifest.csv` has 65 records for 63 unique files: two frozen code files intentionally appear both as source dependencies and as outputs with identical hashes. The manifest excludes itself and interpreter-generated `__pycache__` files.
