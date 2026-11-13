#!/usr/bin/env python3
"""Recreate the timing scenario observation lineage in an isolated output directory."""
import csv
import sys
from pathlib import Path

import run_timing_sensitivity as a


def main(output_path):
    a.check_config()
    prior = a.load('frozen_comparison_readonly', a.RUN / 'run_comparison.py')
    source = a.load('frozen_source_parser_readonly', a.ROOT / 'research/2026-11-06/corrected_four_model_evaluation/build_candidate_xy.py')
    orig = prior.read(prior.HISTORY)
    old = {r['forecast_origin_id']: r for r in orig}
    vix, treasury = source.read_vix(), source.read_treasury()
    hashes = {p.name: a.sha(p) for p in a.RAW.glob('*.csv')}
    candidates = {r['forecast_origin_id'] for r in prior.read(a.RUN / 'candidate_admission_precheck.csv')}
    rows = []
    for scenario, changed in a.SCENARIOS.items():
        updated, _ = a.update_rows(orig, changed, vix, treasury, hashes)
        for r in updated:
            oid = r['forecast_origin_id']
            if oid not in candidates:
                continue
            for feature in changed:
                at = r[feature + '_available_proxy_utc']
                if at and prior.utc(at) > prior.utc(r['forecast_cutoff_utc']):
                    raise ValueError('future feature in lineage: ' + oid + '/' + feature)
                rows.append({'scenario': scenario, 'forecast_origin_id': oid,
                             'forecast_cutoff_utc': r['forecast_cutoff_utc'], 'factor': feature,
                             'original_observation_date': old[oid][feature + '_date'],
                             'scenario_observation_date': r[feature + '_date'],
                             'scenario_value': r[feature],
                             'scenario_available_proxy_utc': at,
                             'source_file': r[feature + '_source_file'],
                             'source_sha256': r[feature + '_source_sha256'],
                             'changed_observation_date': r[feature + '_date'] != old[oid][feature + '_date'],
                             'strict_pit_status': 'UNKNOWN'})
    with Path(output_path).open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print('lineage rows:', len(rows))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: python rebuild_lineage.py /new/output/scenario_feature_lineage.csv')
    main(sys.argv[1])
