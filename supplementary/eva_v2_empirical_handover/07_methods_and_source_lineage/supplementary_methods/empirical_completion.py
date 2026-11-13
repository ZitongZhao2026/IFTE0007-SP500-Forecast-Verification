#!/usr/bin/env python3
"""Saved-output diagnostics and bounded, isolated corrected-model refits.

Never edits the frozen study. Does not select a final model or run a final forecast.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import platform
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import sklearn
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUN = ROOT / "research/2026-11-06/corrected_exploratory_comparison"
FROZEN_NOV6 = ROOT / "research/2026-11-06/nov6_preclose_forecast/frozen_snapshot/frozen_predictions.csv"
HANDOVER_RATE = ROOT / "research/2026-11-09/report_author_handover/06_sensitivity_and_failure_analysis/fixed_rate_sensitivity_recalculated.csv"
CONFIG = HERE / "frozen_analysis_config.json"
CONFIG_HASH = HERE / "frozen_analysis_config.sha256"
FEATURES = ["RET5", "RET20", "RV20", "VIX", "UST10Y", "UST3M", "SPREAD"]
MODEL_NAMES = ["MYSELF", "DMC", "TLJ", "EVA"]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(path, rows):
    if not rows:
        raise ValueError("empty output " + str(path))
    with Path(path).open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load_prior():
    spec = importlib.util.spec_from_file_location("corrected_run_readonly", RUN / "run_comparison.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_config():
    expected = CONFIG_HASH.read_text().split()[0]
    if sha(CONFIG) != expected:
        raise ValueError("frozen config hash mismatch")
    config = json.loads(CONFIG.read_text())
    for rel, digest in config["source_sha256"].items():
        path = ROOT / rel
        if not path.is_file() or sha(path) != digest:
            raise ValueError("source snapshot changed: " + rel)
    if config["research_mode"] != "SUPPLEMENTARY_EXPLORATORY_REFITTING_SENSITIVITY":
        raise ValueError("wrong research mode")
    return config


def metric(rows):
    ape = [100 * abs(float(r["predicted_price"]) - float(r["actual_price"])) / float(r["actual_price"]) for r in rows]
    errors = [float(r["predicted_price"]) - float(r["actual_price"]) for r in rows]
    return {"n": len(rows), "mape_pct": statistics.mean(ape),
            "mae_points": statistics.mean(map(abs, errors)),
            "rmse_points": math.sqrt(statistics.mean(e * e for e in errors))}


def hac_mean(values, lags):
    """Bartlett/Newey-West standard error of a sample mean, fixed lag count."""
    n = len(values)
    m = statistics.mean(values)
    centered = [x - m for x in values]
    long_run = sum(x * x for x in centered) / n
    for lag in range(1, min(lags, n - 1) + 1):
        gamma = sum(centered[t] * centered[t - lag] for t in range(lag, n)) / n
        long_run += 2 * (1 - lag / (lags + 1)) * gamma
    se = math.sqrt(max(0.0, long_run / n))
    p = math.erfc(abs(m / se) / math.sqrt(2)) if se > 0 else 0.0 if m else 1.0
    return {"mean": m, "hac_se": se, "ci95_lower": m - 1.96 * se,
            "ci95_upper": m + 1.96 * se, "normal_approx_p": p, "hac_lags": lags}


def original_membership_refit(prior, hist, members, predictions, eligible):
    """Refit only the frozen seven-factor samples; verify every saved return first."""
    rows = []
    for a in eligible:
        oid = a["forecast_origin_id"]
        member = members[(oid, "MYSELF")]
        ids = member["train_origin_ids"].split("|")
        if len(ids) != int(member["train_count"]):
            raise ValueError("frozen count mismatch " + oid)
        if hashlib.sha256("\n".join(ids).encode()).hexdigest() != member["train_ids_sha256"]:
            raise ValueError("frozen training ID hash mismatch " + oid)
        cutoff = prior.utc(hist[oid]["forecast_cutoff_utc"])
        for i in ids:
            h = hist[i]
            if prior.utc(h["label_available_proxy_utc"]) > cutoff or prior.row_issues(h, FEATURES):
                raise ValueError("immature / invalid frozen training member " + oid + "/" + i)
        X = np.array([[float(hist[i][f]) for f in FEATURES] for i in ids])
        y = np.array([float(hist[i]["return_y"]) for i in ids])
        x = np.array([[float(hist[oid][f]) for f in FEATURES]])
        model = make_pipeline(StandardScaler(), Ridge(alpha=1, solver="auto"))
        model.fit(X, y)
        fitted = float(model.predict(x)[0])
        saved = float(predictions[(oid, "MYSELF")]["predicted_return"])
        if not math.isclose(fitted, saved, abs_tol=1e-10, rel_tol=1e-9):
            raise ValueError(f"frozen prediction not reproduced {oid}: {fitted} vs {saved}")
        scaler, ridge = model.steps[0][1], model.steps[1][1]
        for f, coef in zip(FEATURES, ridge.coef_):
            rows.append({"run_type": "ISOLATED_REFIT_OF_FROZEN_MEMBERSHIP", "forecast_origin_id": oid,
                         "period": a["period"], "year": hist[oid]["forecast_date"][:4],
                         "factor": f, "standardized_coefficient": float(coef),
                         "raw_unit_slope": float(coef) / float(scaler.scale_[FEATURES.index(f)]),
                         "training_count": len(ids), "training_ids_sha256": member["train_ids_sha256"],
                         "fit_cutoff_utc": hist[oid]["forecast_cutoff_utc"],
                         "reproduced_predicted_return": fitted,
                         "saved_predicted_return": saved,
                         "strict_pit_status": "UNKNOWN"})
    return rows


def weekly_train(prior, history, origin, model):
    """Only remove annual origin-date ceiling; preserve each model's feature gate."""
    spec = prior.MODELS[model]
    cutoff = prior.utc(origin["forecast_cutoff_utc"])
    ids = []
    for row in history:
        if not ("2010-01-01" <= row["forecast_date"] < origin["forecast_date"]):
            continue
        if prior.row_issues(row, spec["training_features"]):
            continue
        if prior.utc(row["label_available_proxy_utc"]) > cutoff:
            continue
        ids.append(row["forecast_origin_id"])
    if len(ids) < spec["min_train"]:
        raise ValueError("insufficient weekly training rows")
    return ids


def fit_model(prior, hist, ids, origin, model):
    spec = prior.MODELS[model]
    features = spec["features"]
    X = np.array([[float(hist[i][f]) for f in features] for i in ids])
    y = np.array([float(hist[i]["return_y"]) for i in ids])
    x = np.array([[float(origin[f]) for f in features]])
    if spec["method"] == "RIDGE":
        pipe = make_pipeline(StandardScaler(), Ridge(alpha=1.0, solver=spec["solver"]))
        pipe.fit(X, y)
        return float(pipe.predict(x)[0])
    xm, ym = float(X[:, 0].mean()), float(y.mean())
    denominator = float(((X[:, 0] - xm) ** 2).sum())
    if denominator == 0 and spec["method"] == "OLS_EVA":
        raise ValueError("ZERO_VARIANCE_X")
    slope = 0.0 if denominator == 0 else float(((X[:, 0] - xm) * (y - ym)).sum() / denominator)
    return ym + slope * (float(x[0, 0]) - xm)


def frequency_refit(prior, history, hist, members, predictions, eligible):
    output = []
    for a in eligible:
        if a["period"] != "G3_DEVELOPMENT":
            continue
        oid = a["forecast_origin_id"]
        origin = hist[oid]
        for model in MODEL_NAMES:
            ids = weekly_train(prior, history, origin, model)
            original = members[(oid, model)]
            saved = predictions[(oid, model)]
            if model == "TLJ" and ids != original["train_origin_ids"].split("|"):
                raise ValueError("TLJ originally weekly but membership differs " + oid)
            fitted_return = fit_model(prior, hist, ids, origin, model)
            forecast = float(origin["p0"]) * (1 + fitted_return)
            output.append({"run_type": "SUPPLEMENTARY_EXPLORATORY_REFITTING_SENSITIVITY",
                           "forecast_origin_id": oid, "forecast_date": origin["forecast_date"],
                           "period": a["period"], "model": model,
                           "fit_cutoff_utc": origin["forecast_cutoff_utc"],
                           "p0": origin["p0"], "target_date": origin["target_date"],
                           "actual_price": origin["actual_price"],
                           "predicted_return": fitted_return, "predicted_price": forecast,
                           "training_count": len(ids), "last_train_origin": hist[ids[-1]]["forecast_date"],
                           "max_label_available_at_utc": max(hist[i]["label_available_proxy_utc"] for i in ids),
                           "training_ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(),
                           "original_training_count": original["train_count"],
                           "original_predicted_price": saved["predicted_price"],
                           "strict_pit_status": "UNKNOWN"})
    if len(output) != 257 * 4:
        raise ValueError("unexpected refit coverage")
    return output


def paired_and_tail(hist, predictions, eligible, config):
    paired = []
    tail_rows = []
    for a in eligible:
        oid = a["forecast_origin_id"]
        h = hist[oid]
        actual = float(h["actual_price"])
        p0 = float(h["p0"])
        seven = predictions[(oid, "MYSELF")]
        two = predictions[(oid, "DMC")]
        s = float(seven["predicted_price"])
        t = float(two["predicted_price"])
        ape_s, ape_t = 100 * abs(s - actual) / actual, 100 * abs(t - actual) / actual
        paired.append({"forecast_origin_id": oid, "period": a["period"], "year": h["forecast_date"][:4],
                       "forecast_date": h["forecast_date"], "target_date": h["target_date"],
                       "actual_price": actual, "p0": p0,
                       "seven_predicted_price": s, "two_predicted_price": t,
                       "seven_abs_error_points": abs(s - actual), "two_abs_error_points": abs(t - actual),
                       "seven_ape_pct": ape_s, "two_ape_pct": ape_t,
                       "seven_minus_two_ape_pp": ape_s - ape_t,
                       "seven_minus_two_abs_error_points": abs(s - actual) - abs(t - actual),
                       "winner": "SEVEN" if ape_s < ape_t else "TWO" if ape_t < ape_s else "TIE",
                       "realised_forward_return": float(h["return_y"])})
        for model in [*MODEL_NAMES, "NO_CHANGE"]:
            pred = p0 if model == "NO_CHANGE" else float(predictions[(oid, model)]["predicted_price"])
            pred_return = 0.0 if model == "NO_CHANGE" else float(predictions[(oid, model)]["predicted_return"])
            true_return = float(h["return_y"])
            tail_rows.append({"forecast_origin_id": oid, "period": a["period"],
                              "year": h["forecast_date"][:4], "model": model,
                              "actual_return": true_return, "predicted_return": pred_return,
                              "abs_actual_return": abs(true_return), "abs_predicted_return": abs(pred_return),
                              "predicted_smaller_abs_move": abs(pred_return) < abs(true_return),
                              "direction_hit": (pred_return > 0) == (true_return > 0) if pred_return and true_return else False,
                              "ape_pct": 100 * abs(pred - actual) / actual,
                              "absolute_error_points": abs(pred - actual),
                              "tail_bucket": "GE_5_PERCENT" if abs(true_return) >= 0.05 else "GE_2_LT_5_PERCENT" if abs(true_return) >= 0.02 else "LT_2_PERCENT"})
    return paired, tail_rows


def grouped_outputs(paired, tail_rows, config):
    paired_stats = []
    for period in ("G3_DEVELOPMENT", "G4_PREVIOUSLY_EXPOSED_NON_INDEPENDENT"):
        p = [r for r in paired if r["period"] == period]
        d = [r["seven_minus_two_ape_pp"] for r in p]
        wins = Counter(r["winner"] for r in p)
        extreme = sorted(p, key=lambda r: abs(r["seven_minus_two_ape_pp"]), reverse=True)[:5]
        stats = hac_mean(d, config["hac_lags"])
        paired_stats.append({"period": period, "n": len(p), "seven_wins": wins["SEVEN"],
                             "two_wins": wins["TWO"], "ties": wins["TIE"],
                             "median_seven_minus_two_ape_pp": statistics.median(d), **stats,
                             "top5_abs_diff_sum_pp": sum(abs(r["seven_minus_two_ape_pp"]) for r in extreme),
                             "top5_signed_diff_sum_pp": sum(r["seven_minus_two_ape_pp"] for r in extreme),
                             "sum_all_signed_diff_pp": sum(d),
                             "top5_origin_ids": "|".join(r["forecast_origin_id"] for r in extreme)})
    tail_summary = []
    for (period, bucket, model), grp in sorted(_group(tail_rows, "period", "tail_bucket", "model").items()):
        tail_summary.append({"period": period, "tail_bucket": bucket, "model": model,
                             "n": len(grp), "mean_ape_pct": statistics.mean(r["ape_pct"] for r in grp),
                             "mean_ae_points": statistics.mean(r["absolute_error_points"] for r in grp),
                             "direction_hit_count": sum(r["direction_hit"] for r in grp),
                             "predicted_smaller_abs_move_count": sum(r["predicted_smaller_abs_move"] for r in grp),
                             "mean_abs_actual_return": statistics.mean(r["abs_actual_return"] for r in grp),
                             "mean_abs_predicted_return": statistics.mean(r["abs_predicted_return"] for r in grp)})
    return paired_stats, tail_summary


def _group(rows, *columns):
    d = defaultdict(list)
    for r in rows:
        d[tuple(r[c] for c in columns)].append(r)
    return d


def rate_check():
    row = next(r for r in read(FROZEN_NOV6) if r["model_id"] == "MYSELF_7F_RIDGE")
    detail = json.loads(row["estimator_details_json"])
    names = row["feature_names"].split("|")
    coef = dict(zip(names, detail["coefficients_scaled"]))
    scale = dict(zip(names, detail["scaler_scale"]))
    p0 = float(row["p0"])
    scenarios = {
        "LONG_END_ONLY_10Y_PLUS_25_BP": {"UST10Y": 0.25, "SPREAD": 0.25},
        "PARALLEL_3M_2Y_10Y_PLUS_25_BP": {"UST10Y": 0.25, "UST3M": 0.25},
    }
    old = {r["scenario"]: r for r in read(HANDOVER_RATE)}
    result = []
    for scenario, delta in scenarios.items():
        dr = sum(coef[f] * v / scale[f] for f, v in delta.items())
        dp = p0 * dr
        if not math.isclose(dp, float(old[scenario]["delta_predicted_price_points"]), abs_tol=1e-10):
            raise ValueError("25bp saved recalculation mismatch")
        result.append({"scenario": scenario, "source_origin": row["forecast_origin_id"],
                       "p0": p0, "delta_return": dr, "delta_price_index_points": dp,
                       "saved_snapshot_sha256": sha(FROZEN_NOV6), "previous_recalculation_sha256": sha(HANDOVER_RATE)})
    return row, result


def main():
    config = check_config()
    prior = load_prior()
    prior.verify_input_hashes()
    history = prior.read(prior.HISTORY)
    hist = {r["forecast_origin_id"]: r for r in history}
    admission = prior.read(prior.HERE / "frozen_admission.csv")
    eligible = [r for r in admission if r["common_eligible"] == "YES"]
    if len(eligible) != 413 or Counter(a["period"] for a in eligible) != {"G3_DEVELOPMENT": 257, "G4_PREVIOUSLY_EXPOSED_NON_INDEPENDENT": 156}:
        raise ValueError("frozen common sample changed")
    members = {(r["forecast_origin_id"], r["model"]): r for r in prior.read(prior.HERE / "frozen_training_membership.csv")}
    predictions = {(r["forecast_origin_id"], r["model"]): r for r in prior.read(prior.HERE / "predictions.csv")}
    if len(predictions) != 1652:
        raise ValueError("saved predictions changed")
    paired, tail_rows = paired_and_tail(hist, predictions, eligible, config)
    paired_stats, tail_summary = grouped_outputs(paired, tail_rows, config)
    write(HERE / "paired_ridge_analysis.csv", paired)
    write(HERE / "paired_ridge_summary.csv", paired_stats)
    write(HERE / "tail_error_by_origin.csv", tail_rows)
    write(HERE / "tail_error_diagnostics.csv", tail_summary)
    case = next(r for r in paired if r["forecast_origin_id"] == "F20250328")
    (HERE / "tail_case_2025_03_28.json").write_text(json.dumps(case, indent=2) + "\n")
    frozen_row, rate = rate_check()
    write(HERE / "rate_sensitivity_arithmetic.csv", rate)
    coeff = original_membership_refit(prior, hist, members, predictions, eligible)
    write(HERE / "coefficient_refit_by_origin.csv", coeff)
    summary = []
    for (period, f), grp in sorted(_group(coeff, "period", "factor").items()):
        vals = [r["standardized_coefficient"] for r in grp]
        byyear = _group(grp, "year")
        summary.append({"period": period, "factor": f, "n": len(vals),
                        "positive_count": sum(x > 0 for x in vals), "negative_count": sum(x < 0 for x in vals),
                        "zero_count": sum(x == 0 for x in vals),
                        "positive_share": sum(x > 0 for x in vals) / len(vals),
                        "negative_share": sum(x < 0 for x in vals) / len(vals),
                        "mean_scaled_coef": statistics.mean(vals), "median_scaled_coef": statistics.median(vals),
                        "min_scaled_coef": min(vals), "max_scaled_coef": max(vals),
                        "yearly_positive_share": "|".join(y + ":" + str(round(sum(r["standardized_coefficient"] > 0 for r in sub) / len(sub), 4)) for (y,), sub in sorted(byyear.items())),
                        "origin": "ISOLATED_REFIT_OF_FROZEN_MEMBERSHIP_NOT_SAVED_ORIGINAL_COEFFICIENTS"})
    write(HERE / "coefficient_sign_stability.csv", summary)
    weekly = frequency_refit(prior, history, hist, members, predictions, eligible)
    write(HERE / "refit_frequency_sensitivity/weekly_refit_predictions.csv", weekly)
    metrics = []
    for model in MODEL_NAMES:
        new = [r for r in weekly if r["model"] == model]
        saved = [{**r, "predicted_price": r["original_predicted_price"]} for r in new]
        a, b = metric(new), metric(saved)
        metrics.append({"model": model, "n": len(new),
                        "weekly_mape_pct": a["mape_pct"], "weekly_mae_points": a["mae_points"],
                        "weekly_rmse_points": a["rmse_points"],
                        "original_mape_pct_same_origins": b["mape_pct"],
                        "original_mae_points_same_origins": b["mae_points"],
                        "original_rmse_points_same_origins": b["rmse_points"],
                        "weekly_minus_original_mape_pp": a["mape_pct"] - b["mape_pct"],
                        "mean_new_train_n": statistics.mean(int(r["training_count"]) for r in new),
                        "mean_original_train_n": statistics.mean(int(r["original_training_count"]) for r in new),
                        "mean_additional_train_n": statistics.mean(int(r["training_count"]) - int(r["original_training_count"]) for r in new)})
    write(HERE / "refit_frequency_sensitivity/metrics.csv", metrics)
    yearly = []
    grouped = defaultdict(list)
    for r in weekly:
        grouped[(r["model"], r["forecast_date"][:4])].append(r)
    for (model, year), grp in sorted(grouped.items()):
        yearly.append({"model": model, "year": year, **metric(grp)})
    write(HERE / "refit_frequency_sensitivity/yearly_metrics.csv", yearly)
    (HERE / "run_summary.json").write_text(json.dumps({"python": platform.python_version(), "numpy": np.__version__, "sklearn": sklearn.__version__,
        "input_config_sha256": sha(CONFIG), "eligible_g3": 257, "eligible_g4": 156,
        "saved_predictions_reproduced": 413, "weekly_refit_predictions": len(weekly),
        "paired": paired_stats, "weekly_metrics": metrics, "rate": rate,
        "tail_ge2_counts": {p: sum(r["tail_bucket"] != "LT_2_PERCENT" and r["period"] == p and r["model"] == "MYSELF" for r in tail_rows) for p in ("G3_DEVELOPMENT", "G4_PREVIOUSLY_EXPOSED_NON_INDEPENDENT")}}, indent=2) + "\n")
    print("PASS saved predictions reproduced=413; weekly G3 fits=", len(weekly))


if __name__ == "__main__":
    main()
