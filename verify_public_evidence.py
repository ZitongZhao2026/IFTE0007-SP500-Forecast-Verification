#!/usr/bin/env python3
"""Verify public saved evidence using only the standard library; never fit models."""
from pathlib import Path
from decimal import Decimal
import csv,hashlib,json,re
ROOT=Path(__file__).resolve().parent
def rows(rel):
 with (ROOT/rel).open(newline='') as f:return list(csv.DictReader(f))
def main():
 listed=rows('PUBLIC_FILE_HASHES.csv')
 actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name!='PUBLIC_FILE_HASHES.csv'}
 assert {r['path'] for r in listed}==actual,'inventory coverage mismatch'
 for r in listed:
  b=(ROOT/r['path']).read_bytes()
  assert len(b)==int(r['bytes']) and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
 links=0
 for name in ['README.md','EVIDENCE_INDEX.md','PUBLIC_RELEASE_SCOPE.md']:
  for target in re.findall(r'\]\(([^)]+)\)',(ROOT/name).read_text()):
   if '://' in target or target.startswith('#'):continue
   assert (ROOT/target.split('#')[0]).is_file(),f'broken public link: {name}: {target}'
   links+=1
 for r in rows('PUBLIC_REFERENCE_MAP.csv'):
  if r['status']=='INCLUDED':assert (ROOT/r['public_path']).is_file()
 for r in rows('PUBLICATION_MANIFEST.csv'):
  if r['action']=='COPIED_EXACT':assert hashlib.sha256((ROOT/r['public_path']).read_bytes()).hexdigest()==r['source_sha256']
 for r in rows('supplementary/eva_v2_empirical_handover/02_paired_ridge_comparison/paired_ridge_summary.csv'):
  assert sum(int(r[k]) for k in ['seven_wins','two_wins','ties'])==int(r['n'])
  mean,se=float(r['mean']),float(r['hac_se'])
  assert abs(float(r['ci95_lower'])-(mean-1.96*se))<1e-10
  assert abs(float(r['ci95_upper'])-(mean+1.96*se))<1e-10
 for r in rows('supplementary/eva_v2_empirical_handover/06_tail_and_rate_sensitivity/rate_sensitivity_arithmetic.csv'):
  assert abs(Decimal(r['p0'])*Decimal(r['delta_return'])-Decimal(r['delta_price_index_points']))<Decimal('1e-12')
 for r in rows('supplementary/eva_v2_empirical_handover/03_coefficient_signs/coefficient_sign_stability.csv'):
  assert sum(int(r[k]) for k in ['positive_count','negative_count','zero_count'])==int(r['n'])
 for p in (ROOT/'evidence/provider_metadata').glob('*.json'):
  m=json.loads(p.read_text());assert 'raw_path' not in m
  assert m['_public_projection']['removed_field']=='raw_path'
  assert m['historical_first_available_at']=='UNKNOWN'
 print(f'PASS: {len(listed)} hashes; {links} navigation links; exact evidence copies; paired/HAC/rate/sign summary arithmetic; labelled provider metadata projections')
 print('LIMIT: saved evidence only; no financial inputs, historical publication certification, model fitting or full retraining')
if __name__=='__main__':main()
