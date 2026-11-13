#!/usr/bin/env python3
"""Two pre-frozen, one-source-at-a-time T+3 proxy-delay sensitivities.

This is a counterfactual research calculation, never a real release-time claim.
The unchanged price rule leaves P0, target price, and label maturity untouched.
"""
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = HERE.parent
RUN = ROOT / 'research/2026-11-06/corrected_exploratory_comparison'
RAW = ROOT / 'research/2026-10-28/g1_vix_treasury/raw'
NY = ZoneInfo('America/New_York')
NAMES = ('MYSELF', 'DMC', 'TLJ', 'EVA')
SCENARIOS = {'VIX_T_PLUS_3_NY_DAYS': ('VIX',),
             'TREASURY_T_PLUS_3_NY_DAYS': ('UST10Y', 'UST3M', 'UST2Y', 'SPREAD')}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(name, rows):
    if not rows:
        raise ValueError('empty output: ' + name)
    with (HERE / name).open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def proxy(d, days=3):
    return datetime.combine(d + timedelta(days=days), time(23, 59, 59), NY).astimezone(timezone.utc)


def check_config():
    path = HERE / 'timing_config.json'
    expected = (HERE / 'timing_config.sha256').read_text().split()[0]
    if sha(path) != expected:
        raise ValueError('timing config hash mismatch')
    cfg = json.loads(path.read_text())
    for rel, digest in cfg['source_sha256'].items():
        if sha(ROOT / rel) != digest:
            raise ValueError('source hash mismatch: ' + rel)
    if cfg['scenarios'] != {k: list(v) for k, v in SCENARIOS.items()}:
        raise ValueError('scenario set changed')
    return cfg


def update_rows(history, features, vix, treasury, raw_hashes):
    new = []
    change_count = Counter()
    changed = set(features)
    for old in history:
        r = dict(old)
        cutoff = datetime.fromisoformat(r['forecast_cutoff_utc'])
        origin = date.fromisoformat(r['forecast_date'])
        reasons = {reason for reason in r['reasons'].split('|') if reason and not any(reason.endswith('_' + f) for f in changed)}
        for name in features:
            source = vix if name == 'VIX' else treasury
            getter = (lambda x: x) if name == 'VIX' else \
                (lambda x: None if x['10Y'] is None or x['2Y'] is None else x['10Y'] - x['2Y']) if name == 'SPREAD' else \
                (lambda x, tenor={'UST10Y': '10Y', 'UST3M': '3M', 'UST2Y': '2Y'}[name]: x[tenor])
            eligible_dates = [d for d in source if proxy(d) <= cutoff]
            good = [d for d in eligible_dates if getter(source[d]) is not None]
            selected = max(good) if good else None
            value = getter(source[selected]) if selected else None
            at = proxy(selected) if selected else None
            prior_date = r[name + '_date']
            r[name] = value if value is not None else ''
            r[name + '_date'] = selected.isoformat() if selected else ''
            r[name + '_available_proxy_utc'] = at.isoformat() if at else ''
            if prior_date != r[name + '_date']:
                change_count[name] += 1
            if selected is None:
                reasons.add('MISSING_' + name)
                r[name + '_staleness_status'] = 'UNKNOWN_SOURCE_SPECIFIC_SESSION_CALENDAR'
                r[name + '_source_file'] = ''
                r[name + '_source_sha256'] = ''
                continue
            if not math.isfinite(float(value)):
                reasons.add('NONFINITE_' + name)
            if any(d > selected and getter(source[d]) is None for d in eligible_dates):
                reasons.add('KNOWN_LATER_SOURCE_RECORD_MISSING_' + name)
            age = (origin - selected).days
            r[name + '_staleness_status'] = ('WITHIN_FIVE_CALENDAR_DAYS_CONSERVATIVE_UPPER_BOUND'
                                           if age <= 5 else 'UNKNOWN_SOURCE_SPECIFIC_SESSION_CALENDAR')
            if age > 5:
                reasons.add('STALE_OR_SOURCE_SESSION_COUNT_UNKNOWN_' + name)
            filename = ('VIX_History.csv' if name == 'VIX' else
                        'yield-curve-rates-1990-2024.csv' if selected.year <= 2024 else
                        'daily-treasury-rates-2025.csv' if selected.year == 2025 else
                        'daily-treasury-rates-2026.csv')
            r[name + '_source_file'] = str((RAW / filename).relative_to(ROOT))
            r[name + '_source_sha256'] = raw_hashes[filename]
        r['reasons'] = '|'.join(sorted(reasons))
        r['research_candidate_status'] = 'BLOCKED' if reasons else 'EXPLORATORY_CANDIDATE_NOT_FORMAL_PASS'
        r['strict_pit_status'] = 'STRICT_PIT_UNKNOWN'
        new.append(r)
    return new, change_count


def issues(prior, row, model_features, changed):
    base = prior.row_issues(row, model_features)
    base = [x for x in base if x not in {'BAD_PROXY_TIME_' + f for f in changed}]
    cutoff = prior.utc(row['forecast_cutoff_utc'])
    for f in changed:
        if f not in model_features:
            continue
        try:
            d = date.fromisoformat(row[f + '_date'])
            at = prior.utc(row[f + '_available_proxy_utc'])
            if at != proxy(d) or at > cutoff:
                base.append('BAD_ALTERNATE_PROXY_' + f)
        except ValueError:
            base.append('MISSING_ALTERNATE_PROXY_' + f)
    return sorted(set(base))


def main():
    check_config()
    prior = load('frozen_comparison_readonly', RUN / 'run_comparison.py')
    emp = load('base_empirical_readonly', BASE / 'empirical_completion.py')
    factors = load('frozen_source_parser_readonly', ROOT / 'research/2026-11-06/corrected_four_model_evaluation/build_candidate_xy.py')
    prior.verify_input_hashes()
    orig = prior.read(prior.HISTORY)
    orig_byid = {r['forecast_origin_id']: r for r in orig}
    orig_predictions = {(r['forecast_origin_id'], r['model']): r for r in prior.read(RUN / 'predictions.csv')}
    orig_common = {r['forecast_origin_id'] for r in prior.read(RUN / 'frozen_admission.csv') if r['common_eligible'] == 'YES'}
    origins = prior.read(RUN / 'candidate_admission_precheck.csv')
    vix, treasury = factors.read_vix(), factors.read_treasury()
    raw_hashes = {p.name: sha(p) for p in RAW.glob('*.csv')}
    coverage, predictions, training, metrics = [], [], [], []
    for scenario, changed in SCENARIOS.items():
        history, changes = update_rows(orig, changed, vix, treasury, raw_hashes)
        byid = {r['forecast_origin_id']: r for r in history}
        changed_set = set(changed)
        issue_cache = {(r['forecast_origin_id'], model): issues(prior, r, spec['training_features'], changed_set)
                       for r in history for model, spec in prior.MODELS.items()}
        prediction_issue_cache = {(r['forecast_origin_id'], model): issues(prior, r, spec['features'], changed_set)
                                  for r in history for model, spec in prior.MODELS.items()}
        label_times = {r['forecast_origin_id']: prior.utc(r['label_available_proxy_utc'])
                       for r in history if r['label_available_proxy_utc']}
        scenario_ids = []
        for entry in origins:
            oid = entry['forecast_origin_id']
            row = byid[oid]
            model_issues = {}
            memberships = {}
            for model, spec in prior.MODELS.items():
                model_issues[model] = list(prediction_issue_cache[(oid, model)])
                year = int(row['forecast_date'][:4])
                ceiling = f'{year - 1}-12-31' if year <= 2022 and spec['g3_annual_ceiling'] else row['forecast_date']
                train = [h['forecast_origin_id'] for h in history
                         if '2010-01-01' <= h['forecast_date'] < row['forecast_date']
                         and h['forecast_date'] <= ceiling
                         and h['forecast_origin_id'] in label_times
                         and label_times[h['forecast_origin_id']] <= prior.utc(row['forecast_cutoff_utc'])
                         and not issue_cache[(h['forecast_origin_id'], model)]]
                memberships[model] = train
                if len(train) < spec['min_train']:
                    model_issues[model].append('INSUFFICIENT_TRAINING_ROWS')
            eligible = entry['research_candidate_status'] != 'BLOCKED' and not any(model_issues.values())
            # A new time assumption cannot clear previously known price conflict.
            if 'ISOLATED_KNOWN_2019_PRICE_CONFLICT' in row['reasons']:
                eligible = False
            coverage.append({'scenario': scenario, 'forecast_origin_id': oid,
                             'period': entry['period'], 'status': 'ELIGIBLE' if eligible else 'BLOCKED',
                             'reason': '|'.join(f'{m}:{";".join(v)}' for m, v in model_issues.items() if v)
                             or row['reasons'], 'original_common_eligible': oid in orig_common,
                             'changed_feature_count': sum(row[f + '_date'] != orig_byid[oid][f + '_date'] for f in changed),
                             'strict_pit_status': 'UNKNOWN'})
            if not eligible:
                continue
            scenario_ids.append(oid)
            for model in NAMES:
                ids = memberships[model]
                fit = emp.fit_model(prior, byid, ids, row, model)
                pred = float(row['p0']) * (1 + fit)
                predictions.append({'scenario': scenario, 'forecast_origin_id': oid,
                                    'period': entry['period'], 'model': model,
                                    'forecast_date': row['forecast_date'], 'target_date': row['target_date'],
                                    'p0': row['p0'], 'actual_price': row['actual_price'],
                                    'predicted_return': fit, 'predicted_price': pred,
                                    'training_count': len(ids), 'training_ids_sha256': hashlib.sha256('\n'.join(ids).encode()).hexdigest(),
                                    'strict_pit_status': 'UNKNOWN'})
                training.append({'scenario': scenario, 'forecast_origin_id': oid, 'model': model,
                                 'train_n': len(ids), 'first_train_origin': ids[0], 'last_train_origin': ids[-1],
                                 'max_label_available_at_utc': max(byid[i]['label_available_proxy_utc'] for i in ids),
                                 'training_ids_sha256': hashlib.sha256('\n'.join(ids).encode()).hexdigest()})
        for period in ('G3_DEVELOPMENT', 'G4_PREVIOUSLY_EXPOSED_NON_INDEPENDENT'):
            p = [r for r in predictions if r['scenario'] == scenario and r['period'] == period]
            ids = {r['forecast_origin_id'] for r in p}
            intersection = ids & orig_common
            for model in NAMES:
                s = [r for r in p if r['model'] == model and r['forecast_origin_id'] in intersection]
                base = [{**r, 'predicted_price': orig_predictions[(r['forecast_origin_id'], model)]['predicted_price']} for r in s]
                if not s:
                    continue
                newm, oldm = emp.metric(s), emp.metric(base)
                metrics.append({'scenario': scenario, 'period': period, 'model': model,
                                'scenario_common_n': len(ids), 'original_common_n': len([x for x in origins if x['period'] == period and x['forecast_origin_id'] in orig_common]),
                                'intersection_n': len(intersection), 'source_observation_date_changed_count': json.dumps(dict(changes), sort_keys=True),
                                'scenario_mape_on_intersection_pct': newm['mape_pct'],
                                'saved_mape_on_intersection_pct': oldm['mape_pct'],
                                'delta_mape_pp_on_intersection': newm['mape_pct'] - oldm['mape_pct'],
                                'scenario_mae_points': newm['mae_points'], 'scenario_rmse_points': newm['rmse_points']})
    write('scenario_coverage.csv', coverage)
    write('scenario_predictions.csv', predictions)
    write('scenario_training_manifest.csv', training)
    write('scenario_metrics.csv', metrics)
    (HERE / 'scenario_summary.json').write_text(json.dumps({'scenario_config_sha256': sha(HERE / 'timing_config.json'),
        'counts': {s: dict(Counter(r['period'] for r in coverage if r['scenario'] == s and r['status'] == 'ELIGIBLE')) for s in SCENARIOS},
        'changed_dates': {s: dict(Counter(r['forecast_origin_id'][:5] for r in coverage if r['scenario'] == s and r['changed_feature_count'] > 0)) for s in SCENARIOS},
        'strict_pit_status': 'UNKNOWN'}, indent=2) + '\n')
    print('PASS scenarios', {s: sum(r['scenario'] == s and r['status'] == 'ELIGIBLE' for r in coverage) for s in SCENARIOS})


if __name__ == '__main__':
    main()
