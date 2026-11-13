#!/usr/bin/env python3
"""Verify saved public artifacts; this does not reconstruct or refit the forecast."""
import csv
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    with (ROOT / "PUBLIC_FILE_HASHES.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows, "empty hash inventory"
    for row in rows:
        path = ROOT / row["path"]
        assert path.is_file(), f"missing: {row['path']}"
        assert path.stat().st_size == int(row["bytes"]), f"size mismatch: {row['path']}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"], f"hash mismatch: {row['path']}"
    result = json.loads((ROOT / "result/final_forecast_result.json").read_text())
    facts = json.loads((ROOT / "result/public_forecast_facts.json").read_text())
    assert result["model_id"] == "SEVEN_FACTOR_RIDGE"
    assert Decimal(str(result["alpha"])) == Decimal("1")
    assert result["training_count"] == 869
    assert result["target_session"] == "2026-11-20"
    assert result["information_cutoff_timestamp_utc"] == "2026-11-13T12:00:00+00:00"
    assert result["P0_observation_date"] == "2026-11-12"
    assert set(result["features"]) == {"RET5", "RET20", "RV20", "VIX", "UST10Y", "UST3M", "SPREAD"}
    assert result["strict_pit_status"] == "STRICT_PIT_UNKNOWN"
    assert result["target_actual_price"] == "NOT_INCLUDED"
    assert result["training_manifest_sha256"] == facts["training_manifest_sha256"]
    assert result["live_bundle_sha256"] == facts["live_bundle_sha256"]
    assert result["execution_manifest_sha256"] == facts["execution_manifest_sha256"]
    p0 = Decimal(facts["p0"])
    prediction = Decimal(str(result["predicted_price"]))
    calculated = p0 * (Decimal(1) + Decimal(str(result["predicted_return"])))
    assert abs(prediction - calculated) < Decimal("0.00000001")
    assert prediction.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("7552.46")
    assert abs(Decimal(str(result["predicted_return"])) * 100 - Decimal("-0.5260040020305717")) < Decimal("0.000000000001")
    print(f"PASS: {len(rows)} saved file hashes; P0={p0}; return={result['predicted_return']}; forecast=7552.46; 869 training rows recorded")
    print("LIMIT: saved-artifact verification only; raw-data reconstruction and model refit not performed")


if __name__ == "__main__":
    main()
