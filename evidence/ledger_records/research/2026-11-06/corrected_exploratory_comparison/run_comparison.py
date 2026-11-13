#!/usr/bin/env python3
"""Frozen, exploratory corrected-proxy comparison; never touches formal evaluator.

Run --prepare first; review frozen rules and membership, then run --execute.
All source observations are candidates; actual release/vintage remains UNKNOWN.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, platform, sys
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HISTORY = HERE / 'historical_candidate_data.csv'
ADMISSION = HERE / 'candidate_admission_precheck.csv'
INPUT_HASHES = HERE / 'input_hashes.csv'
RULES = HERE / 'rules.json'
LINEAGE = HERE / 'price_window_lineage.csv'
CALENDAR = ROOT / 'research/2026-10-29/g2_price_rolling/calendar_daily.csv'
NY = ZoneInfo('America/New_York')
LONDON = ZoneInfo('Europe/London')
SEVEN = ['RET5', 'RET20', 'RV20', 'VIX', 'UST10Y', 'UST3M', 'SPREAD']
MODELS = {
    'MYSELF': {'features': SEVEN, 'training_features': SEVEN, 'method':'RIDGE', 'min_train':10, 'g3_annual_ceiling':True, 'solver':'auto'},
    'DMC': {'features':['VIX','UST10Y'], 'training_features':SEVEN, 'method':'RIDGE', 'min_train':30, 'g3_annual_ceiling':True, 'solver':'svd'},
    'TLJ': {'features':['RV20'], 'training_features':['RV20'], 'method':'OLS_TLJ', 'min_train':30, 'g3_annual_ceiling':False},
    'EVA': {'features':['UST10Y'], 'training_features':['UST10Y'], 'method':'OLS_EVA', 'min_train':52, 'g3_annual_ceiling':True},
}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    with path.open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def write(path, rows, columns=None):
    if path.exists(): raise RuntimeError(f'refusing to overwrite {path}')
    with path.open('x', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=columns or list(rows[0])); w.writeheader(); w.writerows(rows)
def utc(s):
    v=datetime.fromisoformat(s.replace('Z','+00:00'))
    if v.utcoffset() is None: raise ValueError('naive timestamp')
    return v.astimezone(timezone.utc)
def number(value):
    x=float(value)
    if not math.isfinite(x): raise ValueError('nonfinite')
    return x

@lru_cache(maxsize=1)
def calendar():
    data=read(CALENDAR)
    out={r['date']:r['classification'] for r in data}
    if len(out)!=len(data): raise ValueError('duplicate calendar date')
    return out

@lru_cache(maxsize=2048)
def expected_dates(origin_date):
    od=date.fromisoformat(origin_date)
    if od.weekday()!=4: raise ValueError('origin is not Friday')
    cutoff=datetime.combine(od,time(12),LONDON).astimezone(timezone.utc)
    cal=calendar(); nominal=(od+timedelta(days=7)).isoformat()
    if cal.get(nominal) in ('FULL','EARLY'): target=nominal
    elif cal.get(nominal)=='CLOSED_SCHEDULED':
        start=(od+timedelta(days=3)).isoformat()
        prior=[d for d in cal if start<=d<nominal and cal[d] in ('FULL','EARLY')]
        target=max(prior) if prior else ''
    else: target=''
    prior=[d for d in cal if d<origin_date and cal[d] in ('FULL','EARLY') and datetime.combine(date.fromisoformat(d)+timedelta(days=1),time.min,NY).astimezone(timezone.utc)<=cutoff]
    return cutoff, max(prior) if prior else '', target

def row_issues(r, features):
    """Validate a historical row at its own origin; no later cutoff substitution."""
    issues=[]
    try:
        c=utc(r['forecast_cutoff_utc']); p=number(r['p0']); a=number(r['actual_price']); y=number(r['return_y'])
        expected_cutoff, expected_p0, expected_target=expected_dates(r['forecast_date'])
        if c!=expected_cutoff: issues.append('BAD_LONDON_CUTOFF')
        if r['p0_date']!=expected_p0: issues.append('P0_SESSION_MISMATCH')
        if not expected_target or r['target_date']!=expected_target: issues.append('TARGET_SESSION_MISMATCH')
        if p<=0 or a<=0: issues.append('NONPOSITIVE_PRICE')
        if abs(y-(a/p-1))>1e-12: issues.append('TARGET_RETURN_MISMATCH')
        if utc(r['p0_available_proxy_utc'])>c: issues.append('FUTURE_P0')
        expected_p0_time=datetime.combine(date.fromisoformat(r['p0_date'])+timedelta(days=1),time.min,NY).astimezone(timezone.utc)
        expected_label_time=datetime.combine(date.fromisoformat(r['target_date'])+timedelta(days=1),time.min,NY).astimezone(timezone.utc)
        if utc(r['p0_available_proxy_utc'])!=expected_p0_time: issues.append('BAD_P0_PROXY_TIME')
        if utc(r['label_available_proxy_utc'])!=expected_label_time: issues.append('BAD_LABEL_PROXY_TIME')
        if not (r['p0_date'] < r['forecast_date'] < r['target_date']): issues.append('BAD_DATE_ORDER')
        if utc(r['label_available_proxy_utc'])<=c: issues.append('TARGET_MATURE_AT_OWN_ORIGIN')
    except (ValueError, KeyError, ZeroDivisionError): issues.append('MISSING_INVALID_PRICE_OR_TIME')
    for reason in filter(None,r.get('reasons','').split('|')):
        if reason.startswith(('P0_', 'TARGET_', 'ISOLATED_', 'NONPOSITIVE_', 'NONFINITE_', 'INVALID_')):
            issues.append(reason)
        elif reason=='INCOMPLETE_CONSECUTIVE_PRICE_WINDOW' and any(x in features for x in ('RET5','RET20','RV20')):
            issues.append(reason)
        elif any(reason.endswith('_'+x) for x in features if x in ('VIX','UST10Y','UST3M','UST2Y','SPREAD')):
            issues.append(reason)
    for feature in features:
        try:
            number(r[feature])
            if feature in ('VIX','UST10Y','UST3M','SPREAD'):
                at=utc(r[feature+'_available_proxy_utc']); obs=date.fromisoformat(r[feature+'_date'])
                expected=datetime.combine(obs+timedelta(days=2),time(23,59,59),NY).astimezone(timezone.utc)
                if at!=expected: issues.append('BAD_PROXY_TIME_'+feature)
                if at>c: issues.append('FUTURE_'+feature)
        except (ValueError,KeyError): issues.append('MISSING_INVALID_'+feature)
    return sorted(set(issues))

def eligible_train(rows, origin, model):
    cutoff=utc(origin['forecast_cutoff_utc']); y=int(origin['forecast_date'][:4]); spec=MODELS[model]
    ceiling=f'{y-1}-12-31' if y<=2022 and spec['g3_annual_ceiling'] else origin['forecast_date']
    ids=[]
    for row in rows:
        if not ('2010-01-01'<=row['forecast_date']<origin['forecast_date'] and row['forecast_date']<=ceiling): continue
        if row_issues(row,spec['training_features']): continue
        if utc(row['label_available_proxy_utc'])>cutoff: continue
        ids.append(row['forecast_origin_id'])
    return ids, ceiling

def verify_input_hashes():
    for item in read(INPUT_HASHES):
        p=ROOT/item['path']
        if not p.exists() or sha(p)!=item['sha256']: raise RuntimeError('input hash mismatch: '+str(p))

def prepare():
    verify_input_hashes()
    history=read(HISTORY); admission=read(ADMISSION)
    byid={r['forecast_origin_id']:r for r in history}
    if len(byid)!=len(history) or len(admission)!=417 or len({r['forecast_origin_id'] for r in admission})!=417: raise ValueError('duplicate or missing origins')
    if not set(r['forecast_origin_id'] for r in admission)<=set(byid): raise ValueError('missing historical row')
    common=[]; membership=[]; coverage=[]
    for a in admission:
        row=byid[a['forecast_origin_id']]; base_ok=a['research_candidate_status']!='BLOCKED'
        all_ok=base_ok; per=[]
        for name,spec in MODELS.items():
            problems=row_issues(row,spec['features'])
            ids, ceiling=eligible_train(history,row,name)
            if len(ids)<spec['min_train']: problems.append('INSUFFICIENT_TRAINING_ROWS')
            all_ok=all_ok and not problems
            per.append((name,ids,ceiling,problems))
        if all_ok: common.append(row['forecast_origin_id'])
        for name,ids,ceiling,problems in per:
            membership.append({'forecast_origin_id':row['forecast_origin_id'],'model':name,'fit_cutoff_utc':row['forecast_cutoff_utc'],'train_end_ceiling':ceiling,'train_count':len(ids),'train_ids_sha256':hashlib.sha256('\n'.join(ids).encode()).hexdigest(),'train_origin_ids':'|'.join(ids),'model_issues':'|'.join(problems),'common_input_eligible':'YES' if all_ok else 'NO','strict_pit_status':'STRICT_PIT_UNKNOWN'})
        coverage.append({'forecast_origin_id':row['forecast_origin_id'],'forecast_date':row['forecast_date'],'period':a['period'],'common_eligible':'YES' if all_ok else 'NO','reason':a['reasons'] if not base_ok else '|'.join(f'{n}:{";".join(i)}' for n,_,_,i in per if i),'strict_pit_status':'STRICT_PIT_UNKNOWN'})
    if len(coverage)!=417: raise ValueError('unexpected coverage')
    write(HERE/'frozen_admission.csv',coverage); write(HERE/'frozen_training_membership.csv',membership)
    # Snapshot before any forecast error is computed. Existing G4 use of per-origin
    # expanding is an explicitly labelled adaptation for models without G4 folds.
    config={'mode':'EXPLORATORY_CORRECTED_PROXY_PIT','status':'RESEARCH_SNAPSHOT_NOT_FORMAL_APPROVAL', 'models':MODELS,'alpha':1.0,'training_start':'2010-01-01', 'fit_cutoff':'each origin cutoff', 'g3':'2018-2022; annual ceiling for MYSELF/DMC/EVA, weekly TLJ','g4':'2023-2025; per-origin expanding adaptation; previously exposed/non-independent','price_version':'stage2c CRSP/FRED candidate; isolate 2019-08-12 affected windows','rule_hash':sha(RULES),'actual_release_vintage_and_session':'UNKNOWN','scoring':'DIAGNOSTIC_ONLY','frozen_common_origin_ids':common,'input_hashes':{str(p.relative_to(HERE)):sha(p) for p in [HISTORY,ADMISSION,INPUT_HASHES,RULES,LINEAGE,HERE/'frozen_admission.csv',HERE/'frozen_training_membership.csv',Path(__file__).resolve()]},'runtime':{'python':platform.python_version()}}
    snapshot=HERE/'execution_snapshot.json'
    with snapshot.open('x',encoding='utf-8') as f: f.write(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    (HERE/'execution_snapshot.sha256').write_text(sha(snapshot)+'  execution_snapshot.json\n',encoding='utf-8')
    print('FROZEN (no predictions)',len(common),'G3',sum(byid[x]['forecast_date'][:4]<='2022' for x in common),'G4',sum(byid[x]['forecast_date'][:4]>='2023' for x in common))

def execute():
    import numpy as np
    import sklearn
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    snapshot=HERE/'execution_snapshot.json'
    expected=(HERE/'execution_snapshot.sha256').read_text().split()[0]
    if sha(snapshot)!=expected: raise RuntimeError('frozen configuration hash mismatch')
    config=json.loads(snapshot.read_text())
    if config['models']!=MODELS or config['alpha']!=1.0: raise RuntimeError('frozen model configuration mismatch')
    verify_input_hashes()
    for p,h in config['input_hashes'].items():
        if sha(HERE/p)!=h: raise RuntimeError('frozen snapshot mismatch: '+p)
    rows=read(HISTORY); byid={r['forecast_origin_id']:r for r in rows}; coverage=read(HERE/'frozen_admission.csv')
    membership={(r['forecast_origin_id'],r['model']):r for r in read(HERE/'frozen_training_membership.csv')}
    common=config['frozen_common_origin_ids']; predictions=[]; failures=[]
    fixed=[r['forecast_origin_id'] for r in coverage if r['common_eligible']=='YES']
    if common!=fixed or len(set(common))!=len(common): raise RuntimeError('frozen common set mismatch')
    for origin_id in common:
        origin=byid[origin_id]
        for model,spec in MODELS.items():
            member=membership[(origin_id,model)]; ids=member['train_origin_ids'].split('|') if member['train_origin_ids'] else []
            # Recompute and reject any altered membership or immature training label.
            expected, ceiling=eligible_train(rows,origin,model)
            if ids!=expected or ceiling!=member['train_end_ceiling'] or row_issues(origin,spec['features']): raise RuntimeError('gate mismatch '+origin_id+' '+model)
            X=np.array([[number(byid[i][f]) for f in spec['features']] for i in ids],dtype=float)
            Y=np.array([number(byid[i]['return_y']) for i in ids],dtype=float)
            x=np.array([[number(origin[f]) for f in spec['features']]],dtype=float)
            try:
                if spec['method']=='RIDGE':
                    est=make_pipeline(StandardScaler(),Ridge(alpha=1.0,solver=spec['solver']))
                    est.fit(X,Y); yh=float(est.predict(x)[0])
                else:
                    xm=float(X[:,0].mean()); ym=float(Y.mean()); denom=float(((X[:,0]-xm)**2).sum())
                    if denom==0 and spec['method']=='OLS_EVA': raise ValueError('ZERO_VARIANCE_X')
                    slope=0.0 if denom==0 else float(((X[:,0]-xm)*(Y-ym)).sum()/denom)
                    yh=ym+slope*(float(x[0,0])-xm)
                pred=number(origin['p0'])*(1+yh)
                if not math.isfinite(pred): raise ValueError('NONFINITE_PREDICTION')
                predictions.append({'forecast_origin_id':origin_id,'forecast_date':origin['forecast_date'],'period':'G3_DEVELOPMENT' if origin['forecast_date'][:4]<='2022' else 'G4_PREVIOUSLY_EXPOSED_NON_INDEPENDENT','model':model,'forecast_cutoff_utc':origin['forecast_cutoff_utc'],'fit_cutoff_utc':origin['forecast_cutoff_utc'],'p0':origin['p0'],'p0_date':origin['p0_date'],'target_date':origin['target_date'],'actual_price_candidate':origin['actual_price'],'predicted_return':yh,'predicted_price':pred,'training_count':len(ids),'training_ids_sha256':member['train_ids_sha256'],'status':'PREDICTED_DIAGNOSTIC','strict_pit_status':'STRICT_PIT_UNKNOWN'})
            except Exception as e: failures.append({'forecast_origin_id':origin_id,'model':model,'error':str(e)})
    if failures:
        write(HERE/'execution_failures.csv',failures)
        raise RuntimeError('prediction failure; no metrics, fixed sample retained')
    write(HERE/'predictions.csv',predictions)
    # Scores are generated only on the exact frozen set, never on a post-error intersection.
    grouped={}
    for r in predictions:
        y=number(r['actual_price_candidate']); e=number(r['predicted_price'])-y
        r['_ape']=100*abs(e)/y; r['_ae']=abs(e); r['_sq']=e*e
        grouped.setdefault((r['period'],r['model']),[]).append(r)
    metrics=[]; yearly=[]; pairs=[]
    for (period,model), group in sorted(grouped.items()):
        def measure(g): return {'n':len(g),'MAPE_percent':sum(r['_ape'] for r in g)/len(g),'MAE_points':sum(r['_ae'] for r in g)/len(g),'RMSE_points':math.sqrt(sum(r['_sq'] for r in g)/len(g))}
        metrics.append({'period':period,'model':model,**measure(group)})
        for year in sorted({r['forecast_date'][:4] for r in group}): yearly.append({'period':period,'year':year,'model':model,**measure([r for r in group if r['forecast_date'].startswith(year)])})
    for period in sorted({r['period'] for r in predictions}):
        for i,left in enumerate(MODELS):
            for right in list(MODELS)[i+1:]:
                a={r['forecast_origin_id']:r for r in grouped[(period,left)]}; b={r['forecast_origin_id']:r for r in grouped[(period,right)]}
                if set(a)!=set(b): raise RuntimeError('post-execution sample mismatch')
                ds=[a[k]['_ape']-b[k]['_ape'] for k in sorted(a)]
                pairs.append({'period':period,'model_a':left,'model_b':right,'n':len(ds),'mean_APE_a_minus_b_pp':sum(ds)/len(ds)})
    write(HERE/'metrics.csv',metrics); write(HERE/'yearly_metrics.csv',yearly); write(HERE/'paired_comparison.csv',pairs)
    (HERE/'runtime.json').write_text(json.dumps({'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__},indent=2)+'\n')
    print('completed; frozen sample',len(common),'predictions',len(predictions))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--prepare',action='store_true'); ap.add_argument('--execute',action='store_true'); args=ap.parse_args()
    if args.prepare==args.execute: ap.error('choose exactly --prepare or --execute')
    prepare() if args.prepare else execute()
