#!/usr/bin/env python3
"""Read-only Table A1/A2 recalculation from frozen corrected common origins."""
import csv
import statistics
import sys
from pathlib import Path

import numpy as np


FEATURES = ['RET5', 'RET20', 'RV20', 'VIX', 'UST10Y', 'UST3M', 'SPREAD', 'return_y']


def read(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with Path(path).open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(root, output_dir):
    run = Path(root) / 'research/2026-11-06/corrected_exploratory_comparison'
    hist = {r['forecast_origin_id']: r for r in read(run / 'historical_candidate_data.csv')}
    admission = [r for r in read(run / 'frozen_admission.csv') if r['common_eligible'] == 'YES']
    desc, corr = [], []
    for period in ('G3_DEVELOPMENT', 'G4_PREVIOUSLY_EXPOSED_NON_INDEPENDENT'):
        ids = [r['forecast_origin_id'] for r in admission if r['period'] == period]
        x = np.array([[float(hist[i][f]) for f in FEATURES] for i in ids], dtype=float)
        for j, f in enumerate(FEATURES[:-1]):
            multiplier = 100 if f in ('RET5', 'RET20', 'RV20') else 1
            vals = x[:, j] * multiplier
            desc.append({'period': period, 'factor': f, 'n': len(vals),
                         'display_multiplier': multiplier, 'mean': float(np.mean(vals)),
                         'sample_sd': statistics.stdev(vals)})
        c = np.corrcoef(x, rowvar=False)
        for i, f in enumerate(FEATURES):
            for j, g in enumerate(FEATURES):
                corr.append({'period': period, 'factor_1': f, 'factor_2': g,
                             'pearson_r': float(c[i, j]), 'n': len(ids)})
    write(Path(output_dir) / 'factor_descriptives_recalculated.csv', desc)
    write(Path(output_dir) / 'factor_correlations_recalculated.csv', corr)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: python recalculate_factor_descriptives.py PROJECT_ROOT NEW_OUTPUT_DIR')
    main(sys.argv[1], sys.argv[2])
