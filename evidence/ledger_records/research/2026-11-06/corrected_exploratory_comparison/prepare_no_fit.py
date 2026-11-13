#!/usr/bin/env python3
"""Exploratory preflight only. Never fits a model or computes prediction errors."""
import csv, hashlib, importlib.util, json, statistics, bisect, math
from datetime import date, datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'research/2026-11-05/corrected_proxy_pit_comparison'
PREV=ROOT/'research/2026-11-06/corrected_four_model_evaluation'
RULES=OUT/'rules.json'
def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
p=loadmod('prior_preflight',BASE/'preflight.py')
f=loadmod('prior_factors',PREV/'build_candidate_xy.py')
_hash_cache={}
def sha(path):
    if path not in _hash_cache: _hash_cache[path]=hashlib.sha256(path.read_bytes()).hexdigest()
    return _hash_cache[path]
def check_time(value, cutoff):
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.utcoffset() is None: raise ValueError('naive timestamp')
    return d.astimezone(timezone.utc)<=cutoff.astimezone(timezone.utc)
def rows(path):
    with path.open(newline='',encoding='utf-8-sig') as fp: return list(csv.DictReader(fp))
def write(path, data):
    with path.open('w',newline='',encoding='utf-8') as fp:
        writer=csv.DictWriter(fp,fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)
def main():
    rules=json.loads(RULES.read_text()); assert sha(p.PROTOCOL)==rules['protocol_sha256']
    sources=[RULES,Path(__file__).resolve(),BASE/'preflight.py',PREV/'build_candidate_xy.py',p.PROTOCOL,p.PRICE,p.CAL,p.STAGE2C_SCHEDULE,ROOT/'IFTE0007_Common_Experiment_v1.1/folds.csv',p.MYSELF_CONFIG,p.DMC_ZIP,p.TLJ_ZIP,p.EVA_ZIP,PREV/'corrected_xy_candidate.csv',PREV/'factor_availability_lineage.csv',f.RAW/'VIX_History.csv',f.RAW/'yield-curve-rates-1990-2024.csv',f.RAW/'daily-treasury-rates-2025.csv']
    prices=rows(p.PRICE); price={r['observation_date']:r for r in prices}; assert len(price)==len(prices)
    calrows=rows(p.CAL); cal={r['date']:r for r in calrows}; assert len(cal)==len(calrows)
    sessions=sorted(d for d,r in cal.items() if r['classification'] in {'FULL','EARLY'})
    conflict={d for d,r in price.items() if r.get('conflict_id') or r.get('overlap_comparison_status')=='MATERIAL_CONFLICT'}
    vix,tsy=f.read_vix(),f.read_treasury()
    date_cache={d:f.proxy_at(d) for d in set(vix)|set(tsy)}
    def fast_select(series,cutoff,getval):
        dates=sorted(series); upper=bisect.bisect_right(dates,cutoff.date())
        for d in reversed(dates[:upper]):
            if date_cache[d]<=cutoff and getval(series[d]) is not None: return d,getval(series[d]),date_cache[d]
        return None,None,None
    sources.append(f.RAW/'daily-treasury-rates-2026.csv')
    prev=rows(PREV/'corrected_xy_candidate.csv'); prior={r['forecast_origin_id']:r for r in prev}; assert len(prior)==417
    result=[]; mismatches=[]; price_lineage=[]
    old_lineage={(r['forecast_origin_id'],r['feature_code']):r for r in rows(PREV/'factor_availability_lineage.csv')}
    for s in rows(p.STAGE2C_SCHEDULE):
        od=date.fromisoformat(s['forecast_origin_date'])
        if not (2010<=od.year<=2025): continue
        cutoff=p.friday_cutoff(od); os=od.isoformat(); oid=s['forecast_id']
        if od.weekday()!=4: raise ValueError('non-Friday origin '+oid)
        eligible=[d for d in sessions if d<os and p.proxy_price_available_at(date.fromisoformat(d))<=cutoff]
        pdate=eligible[-1] if eligible else ''; pr=price.get(pdate,{})
        target,ttype,ev=p.target_session(od,cal,set(price))
        # Recheck target without using missing-price dates to choose the fallback.
        nominal=(od+p.timedelta(days=7)).isoformat()
        if cal.get(nominal,{}).get('classification')=='CLOSED_SCHEDULED':
            week=(date.fromisoformat(nominal)-p.timedelta(days=4)).isoformat()
            pool=[d for d in sessions if week<=d<nominal]
            expected=pool[-1] if pool else ''
            if target!=expected: ttype='UNKNOWN'; ev='TARGET_FALLBACK_DISAGREES_WITH_SESSION_CALENDAR'
        tr=price.get(target,{})
        window=[d for d in sessions if d<=pdate][-21:] if pdate else []
        reasons=[]
        if not pdate or not pr.get('index_level'): reasons.append('P0_MISSING_AT_LATEST_EXPECTED_SESSION')
        if ttype=='UNKNOWN' or target not in cal or cal[target]['classification'] not in {'FULL','EARLY'}: reasons.append('TARGET_SESSION_UNKNOWN')
        if not tr.get('index_level'): reasons.append('TARGET_PRICE_MISSING')
        for col,price_row in [('P0',pr),('TARGET',tr)]:
            if price_row.get('index_level'):
                try: valid=math.isfinite(float(price_row['index_level'])) and float(price_row['index_level'])>0
                except (TypeError,ValueError): valid=False
                if not valid: reasons.append('INVALID_'+col+'_PRICE')
        if len(window)!=21 or any(d not in price or not price[d].get('index_level') for d in window): reasons.append('INCOMPLETE_CONSECUTIVE_PRICE_WINDOW')
        if set(window+[pdate,target])&conflict: reasons.append('ISOLATED_KNOWN_2019_PRICE_CONFLICT')
        if pdate and not check_time(p.proxy_price_available_at(date.fromisoformat(pdate)).isoformat(),cutoff): reasons.append('P0_AFTER_CUTOFF')
        rets={}
        if len(window)==21 and not any(x in reasons for x in ('INCOMPLETE_CONSECUTIVE_PRICE_WINDOW','ISOLATED_KNOWN_2019_PRICE_CONFLICT')):
            vals=[float(price[d]['index_level']) for d in window]
            if any(not math.isfinite(x) or x<=0 for x in vals): reasons.append('NONPOSITIVE_PRICE')
            else: rets=p.rolling_values(vals)
        selects={'VIX':fast_select(vix,cutoff,lambda x:x)}
        for tenor in ('10Y','3M','2Y'): selects['UST'+tenor]=fast_select(tsy,cutoff,lambda x,t=tenor:x[t])
        spread={d:v for d,v in tsy.items() if v['10Y'] is not None and v['2Y'] is not None}
        selects['SPREAD']=fast_select(spread,cutoff,lambda x:x['10Y']-x['2Y'])
        row={'forecast_origin_id':oid,'forecast_date':os,'forecast_cutoff_utc':cutoff.isoformat(),'p0_date':pdate,'p0':pr.get('index_level',''),'p0_available_proxy_utc':p.proxy_price_available_at(date.fromisoformat(pdate)).isoformat() if pdate else '', 'p0_source':pr.get('adopted_source',''),'target_date':target,'target_session_evidence':ev,'actual_price':tr.get('index_level',''),'target_source':tr.get('adopted_source',''),'label_available_proxy_utc':p.proxy_price_available_at(date.fromisoformat(target)).isoformat() if tr.get('index_level') else '', 'return_y':float(tr['index_level'])/float(pr['index_level'])-1 if pr.get('index_level') and tr.get('index_level') and 'INVALID_P0_PRICE' not in reasons and 'INVALID_TARGET_PRICE' not in reasons else '', 'price_window_start':window[0] if window else '', 'price_window_end':window[-1] if window else '', 'RET5':rets.get('RET5',''),'RET20':rets.get('RET20',''),'RV20':rets.get('RV20','')}
        for position,wd in enumerate(window):
            source=price.get(wd,{})
            price_lineage.append({'forecast_origin_id':oid,'position':position,'observation_date':wd,'price':source.get('index_level',''),'source':source.get('adopted_source',''),'source_file_sha256':source.get('source_file_sha256',''),'available_at_proxy_utc':p.proxy_price_available_at(date.fromisoformat(wd)).isoformat(),'calendar_status':'UNKNOWN_ACTUAL_SESSION','conflict': 'YES' if wd in conflict else 'NO'})
        for name,(d,val,available) in selects.items():
            row[name]=val if val is not None else ''; row[name+'_date']=d.isoformat() if d else ''; row[name+'_available_proxy_utc']=available.isoformat() if available else ''
            if d is None: reasons.append('MISSING_'+name)
            elif not math.isfinite(float(val)): reasons.append('NONFINITE_'+name)
            elif available>cutoff: reasons.append('FUTURE_'+name)
            source_path=f.RAW/('VIX_History.csv' if name=='VIX' else 'yield-curve-rates-1990-2024.csv' if d and d.year<=2024 else 'daily-treasury-rates-2025.csv') if d else None
            row[name+'_source_file']=str(source_path.relative_to(ROOT)) if source_path else ''
            row[name+'_source_sha256']=sha(source_path) if source_path else ''
            if oid in prior and d:
                oldcode={'SPREAD':'UST10Y_MINUS_UST2Y'}.get(name,name); line=old_lineage.get((oid,oldcode))
                if not line or line['observation_date_candidate']!=d.isoformat() or datetime.fromisoformat(line['available_at_proxy_utc'].replace('Z','+00:00'))!=available or line['source_file_sha256']!=row[name+'_source_sha256']:
                    mismatches.append({'forecast_origin_id':oid,'field':name+'_lineage','new':str(d),'prior':str(line)})
        # Refuse to backfill across a later source record with known missing values.
        raw_series={'VIX': (vix, lambda v: v), 'UST10Y': (tsy, lambda v: v['10Y']), 'UST3M': (tsy, lambda v: v['3M']), 'UST2Y': (tsy, lambda v: v['2Y']), 'SPREAD': (tsy, lambda v: None if v['10Y'] is None or v['2Y'] is None else v['10Y']-v['2Y'])}
        for name,(series,getval) in raw_series.items():
            selected=selects[name][0]
            if selected is not None and any(d>selected and date_cache[d]<=cutoff and getval(v) is None for d,v in series.items()): reasons.append('KNOWN_LATER_SOURCE_RECORD_MISSING_'+name)
            age=(od-selected).days if selected else None
            row[name+'_staleness_status']='WITHIN_FIVE_CALENDAR_DAYS_CONSERVATIVE_UPPER_BOUND' if age is not None and age<=5 else 'UNKNOWN_SOURCE_SPECIFIC_SESSION_CALENDAR'
            if age is not None and age>5: reasons.append('STALE_OR_SOURCE_SESSION_COUNT_UNKNOWN_'+name)
        row['reasons']='|'.join(sorted(set(reasons))); row['research_candidate_status']='BLOCKED' if reasons else 'EXPLORATORY_CANDIDATE_NOT_FORMAL_PASS'; row['strict_pit_status']='STRICT_PIT_UNKNOWN'; row['actual_session_evidence']='UNKNOWN'; result.append(row)
        if oid in prior:
            old=prior[oid]
            for new,oldcol in [('p0_date','p0_date_candidate'),('target_date','target_date_candidate')]:
                if row[new]!=old[oldcol]: mismatches.append({'forecast_origin_id':oid,'field':new,'new':row[new],'prior':old[oldcol]})
            for new,oldcol in [('p0','p0_candidate'),('actual_price','actual_price_candidate'),('RET5','RET5_candidate'),('RET20','RET20_candidate'),('RV20','RV20_candidate'),('VIX','VIX_value_corrected_candidate'),('UST10Y','UST10Y_value_corrected_candidate'),('UST3M','UST3M_value_corrected_candidate'),('UST2Y','UST2Y_value_corrected_candidate'),('SPREAD','UST10Y_MINUS_UST2Y_value_corrected_candidate')]:
                a,b=row[new],old.get(oldcol,'')
                if (str(a)=='' ) != (str(b)=='') or (str(a)!='' and abs(float(a)-float(b))>1e-10): mismatches.append({'forecast_origin_id':oid,'field':new,'new':a,'prior':b})
    if len({r['forecast_origin_id'] for r in result})!=len(result): raise ValueError('duplicate origins')
    byid={r['forecast_origin_id']:r for r in result}; assert set(prior)<=set(byid)
    if mismatches:
        write(OUT/'precheck_mismatches.csv',mismatches)
        print('BLOCKED: mismatches',len(mismatches)); return
    admission=[]
    for old in prev:
        r=byid[old['forecast_origin_id']]; admission.append({'forecast_origin_id':r['forecast_origin_id'],'period':old['period'],'research_candidate_status':r['research_candidate_status'],'reasons':r['reasons'],'strict_pit_status':'STRICT_PIT_UNKNOWN','actual_session_evidence':'UNKNOWN','formal_scoring_status':'NOT_AUTHORIZED'})
    write(OUT/'historical_candidate_data.csv',result); write(OUT/'candidate_admission_precheck.csv',admission); write(OUT/'price_window_lineage.csv',price_lineage)
    write(OUT/'input_hashes.csv',[{'path':str(x.relative_to(ROOT)),'sha256':sha(x)} for x in sources])
    print('history rows',len(result),'candidate origins',len(admission),'eligible by precheck',sum(r['research_candidate_status']!='BLOCKED' for r in admission),'blocked',sum(r['research_candidate_status']=='BLOCKED' for r in admission))
if __name__=='__main__': main()
