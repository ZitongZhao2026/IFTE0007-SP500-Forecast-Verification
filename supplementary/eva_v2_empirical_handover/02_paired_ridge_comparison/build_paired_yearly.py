#!/usr/bin/env python3
"""Build annual paired-Ridge summaries from the saved-origin recalculation."""
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def main(source, output):
    with Path(source).open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    groups = defaultdict(list)
    for r in rows:
        groups[(r['period'], r['year'])].append(r)
    annual = []
    for (period, year), rs in sorted(groups.items()):
        differences = [float(r['seven_minus_two_ape_pp']) for r in rs]
        annual.append({'period': period, 'year': year, 'n': len(rs),
                       'seven_mape_pct': statistics.mean(float(r['seven_ape_pct']) for r in rs),
                       'two_mape_pct': statistics.mean(float(r['two_ape_pct']) for r in rs),
                       'seven_minus_two_mean_ape_pp': statistics.mean(differences),
                       'seven_wins': sum(r['winner'] == 'SEVEN' for r in rs),
                       'two_wins': sum(r['winner'] == 'TWO' for r in rs)})
    with Path(output).open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(annual[0]))
        writer.writeheader()
        writer.writerows(annual)
    print('annual rows:', len(annual))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: python build_paired_yearly.py INPUT.csv NEW_OUTPUT.csv')
    main(sys.argv[1], sys.argv[2])
