#!/usr/bin/env python3
"""One-time approval-gated entry point. Never run without dual-hash approval."""
import argparse
import json
from pathlib import Path
import pipeline_v2_treasury_bound as gate

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--training-csv", type=Path, required=True)
    ap.add_argument("--training-manifest", type=Path, required=True)
    ap.add_argument("--approval-record", type=Path, required=True)
    ap.add_argument("--live-input-snapshot", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        live = json.loads(args.live_input_snapshot.read_text())
        result = gate.run_approved_live_candidate(model_id="SEVEN_FACTOR_RIDGE", training_csv=args.training_csv,
            training_manifest=args.training_manifest, approval_path=args.approval_record,
            live_snapshot=live, live_snapshot_path=args.live_input_snapshot, evidence_root=gate.ROOT,
            rules_path=gate.ROOT / "research/2026-11-06/corrected_exploratory_comparison/rules.json",
            protocol_path=gate.ROOT / "governance/leakage_prevention_protocol.md", output_path=args.output)
    except Exception as exc:
        raise SystemExit(f"BLOCKED: {exc}") from exc
    print(json.dumps({k: result[k] for k in ("model_id", "predicted_return", "predicted_price",
        "training_count", "live_input_status", "strict_pit_status", "execution_manifest_sha256")}, indent=2))

if __name__ == "__main__": main()
