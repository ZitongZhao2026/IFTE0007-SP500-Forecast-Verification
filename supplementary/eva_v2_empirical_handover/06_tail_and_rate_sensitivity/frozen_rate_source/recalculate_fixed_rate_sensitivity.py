#!/usr/bin/env python3
"""Recalculate local fixed-coefficient arithmetic from the saved 6 Nov snapshot.

This does not refit a model or measure an out-of-sample forecast effect.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAVED = HERE / 'project/research/2026-11-06/nov6_preclose_forecast/frozen_snapshot/frozen_predictions.csv'

with SAVED.open(newline='', encoding='utf-8') as f:
    row = next(r for r in csv.DictReader(f) if r['model_id'] == 'MYSELF_7F_RIDGE')
details = json.loads(row['estimator_details_json'])
names = row['feature_names'].split('|')
coef = dict(zip(names, details['coefficients_scaled']))
scale = dict(zip(names, details['scaler_scale']))
p0 = float(row['p0'])

# 25 bp = 0.25 in the stored Treasury percentage-point units.
changes = {
    'LONG_END_ONLY_10Y_PLUS_25_BP': {'UST10Y': 0.25, 'SPREAD': 0.25},
    'PARALLEL_3M_2Y_10Y_PLUS_25_BP': {'UST3M': 0.25, 'UST10Y': 0.25},
}
result = []
for name, delta in changes.items():
    dr = sum(coef[key] * change / scale[key] for key, change in delta.items())
    result.append({'scenario': name, 'forecast_origin_id': row['forecast_origin_id'],
                   'p0': p0, 'delta_predicted_return': dr,
                   'delta_predicted_price_points': p0 * dr,
                   'evidence': 'saved estimator_details_json; fixed coefficients/scales; no refit'})
with (HERE / 'fixed_rate_sensitivity_recalculated.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(result[0]))
    w.writeheader()
    w.writerows(result)
print(result)
