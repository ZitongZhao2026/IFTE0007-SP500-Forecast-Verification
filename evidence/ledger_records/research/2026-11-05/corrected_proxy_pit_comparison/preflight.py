#!/usr/bin/env python3
"""Build a candidate-only price/X-Y and source-availability preflight.

No models are trained. Inputs are read-only snapshots; output rows remain
unadmitted while calendar completeness or source-specific availability is UNKNOWN.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
COMMON = ROOT / "IFTE0007_Common_Experiment_v1.1"
PRICE = COMMON / "stage2c_reference_prices_candidate.csv"
CAL = ROOT / "research/2026-10-29/g2_price_rolling/calendar_daily.csv"
G3 = ROOT / "research/2026-10-29/g3_main_experiment/g3_predictions.csv"
G4 = ROOT / "research/2026-10-29/g4_proxy_temporal_evaluation/g4_predictions.csv"
OLD_G2 = ROOT / "research/2026-10-29/g2_full_history/weekly_xy_candidates.csv"
STAGE2C_SCHEDULE = COMMON / "stage2c_schedule_candidate.csv"
CAL_EVIDENCE = COMMON / "stage2c_calendar_evidence.csv"
FEATURE_TIME = ROOT / "research/2026-10-29/g3c_round4_extended_factors/g3c_round4_source_time_audit.csv"
G3_CONFIG = ROOT / "research/2026-10-29/g3_main_experiment/g3_model_configs.json"
G4_CONFIG = ROOT / "research/2026-10-29/g4_proxy_temporal_evaluation/g4_frozen_config.json"
MYSELF_CONFIG = COMMON / "group_submissions/member_myself/model_config.json"
DMC_ZIP = COMMON / "group_submissions/member_dmc/Ridge_VIX_UST10Y_20261102.zip"
TLJ_ZIP = COMMON / "group_submissions/member_tlj/TLJ_group_submission.zip"
EVA_ZIP = COMMON / "group_submissions/member_eva/MEMBER_ID_PENDING_Eva.zip"
RAW_VIX = ROOT / "research/2026-10-28/g1_vix_treasury/raw/VIX_History.csv"
RAW_TREASURY = [ROOT / "research/2026-10-28/g1_vix_treasury/raw/yield-curve-rates-1990-2024.csv",
                ROOT / "research/2026-10-28/g1_vix_treasury/raw/daily-treasury-rates-2025.csv",
                ROOT / "research/2026-10-28/g1_vix_treasury/raw/daily-treasury-rates-2026.csv"]
PROTOCOL = ROOT / "governance/leakage_prevention_protocol.md"
NY = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")
PRICE_FEATURES = ("RET5", "RET20", "RV20")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def proxy_price_available_at(observation: date) -> datetime:
    """Authorized price-only proxy: next NY natural day at midnight."""
    return datetime.combine(observation + timedelta(days=1), time.min, tzinfo=NY).astimezone(timezone.utc)


def friday_cutoff(origin: date) -> datetime:
    return datetime.combine(origin, time(12), tzinfo=LONDON).astimezone(timezone.utc)


def target_session(origin: date, calendar: dict[str, dict], price_dates: set[str]) -> tuple[str, str, str]:
    nominal = origin + timedelta(days=7)
    row = calendar.get(nominal.isoformat())
    if not row:
        return nominal.isoformat(), "UNKNOWN", "CALENDAR_DATE_NOT_RECORDED"
    cls = row["classification"]
    if cls in {"FULL", "EARLY"}:
        return nominal.isoformat(), "CANDIDATE_SESSION", "RULE_CALENDAR_ONLY_COMPLETENESS_UNKNOWN"
    if cls == "CLOSED_SCHEDULED":
        week_start = nominal - timedelta(days=4)
        earlier = [d for d, c in calendar.items()
                   if week_start.isoformat() <= d < nominal.isoformat()
                   and c["classification"] in {"FULL", "EARLY"} and d in price_dates]
        if not earlier:
            return nominal.isoformat(), "UNKNOWN", "NO_CANDIDATE_PRIOR_SESSION_IN_TARGET_WEEK"
        return max(earlier), "PROXY_FALLBACK_SESSION", "SCHEDULED_CLOSE_FROM_RULE_CALENDAR_COMPLETENESS_UNKNOWN"
    return nominal.isoformat(), "UNKNOWN", f"TARGET_CLASS_{cls}_NOT_ADJUDICATED"


def rolling_values(window_prices: list[float]) -> dict[str, float]:
    if len(window_prices) < 21:
        return {}
    import math
    rets = [window_prices[i] / window_prices[i - 1] - 1 for i in range(1, len(window_prices))]
    mean = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - mean) ** 2 for x in rets) / (len(rets) - 1))
    return {"RET5": window_prices[-1] / window_prices[-6] - 1,
            "RET20": window_prices[-1] / window_prices[-21] - 1,
            "RV20": sd}


def model_row_admissible(*, feature_available_at: str, cutoff_utc: str,
                         calendar_status: str, source_rule_status: str,
                         conflict_isolated: bool, label_available_at: str | None = None,
                         require_label: bool = False) -> bool:
    """Fail-closed row gate used by tests and preflight status calculation."""
    def aware(s: str) -> datetime:
        value = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone")
        return value.astimezone(timezone.utc)
    cut = aware(cutoff_utc)
    if aware(feature_available_at) > cut:
        return False
    if calendar_status != "PASS" or source_rule_status != "PASS" or conflict_isolated:
        return False
    if require_label:
        if not label_available_at or aware(label_available_at) > cut:
            return False
    return True


def load_origin_rows() -> list[dict[str, str]]:
    seen = {}
    for path, period in ((G3, "G3_DEVELOPMENT"), (G4, "G4_PREVIOUSLY_EXPOSED_NON_INDEPENDENT")):
        for r in read_csv(path):
            origin_id = r["forecast_origin_id"]
            origin = r["forecast_origin_date"]
            if origin_id in seen and seen[origin_id]["forecast_origin_date"] != origin:
                raise ValueError(f"origin ID collision: {origin_id}")
            seen[origin_id] = {"forecast_origin_id": origin_id, "forecast_origin_date": origin,
                               "period": period}
    return sorted(seen.values(), key=lambda r: r["forecast_origin_date"])


def build() -> dict:
    input_paths = [PRICE, CAL, G3, G4, OLD_G2, STAGE2C_SCHEDULE, CAL_EVIDENCE, FEATURE_TIME,
                   G3_CONFIG, G4_CONFIG, MYSELF_CONFIG, DMC_ZIP, TLJ_ZIP, EVA_ZIP, RAW_VIX,
                   *RAW_TREASURY, PROTOCOL, OUT / "corrected_proxy_config.json"]
    missing = [str(p.relative_to(ROOT)) for p in input_paths if not p.exists()]
    if missing:
        raise FileNotFoundError("required inputs missing: " + ", ".join(missing))
    protocol_sha = sha(PROTOCOL)
    if protocol_sha != "b80853fb0fa9135d58cf4e3d0c308bc11e354db6ade78b90dadf51814f71b706":
        raise ValueError("approved protocol hash mismatch")

    prices = {}
    for r in read_csv(PRICE):
        d = r["observation_date"]
        if d in prices:
            raise ValueError(f"duplicate reference price date {d}")
        prices[d] = r
    calendar_rows = read_csv(CAL)
    calendar = {r["date"]: r for r in calendar_rows}
    sessions = sorted(d for d, r in calendar.items() if r["classification"] in {"FULL", "EARLY"})
    price_dates = set(prices)
    # Alternate values are normal overlap-comparison evidence; only an explicitly
    # adjudicated material conflict is isolated.
    conflict_dates = {d for d, r in prices.items()
                      if r.get("conflict_id") or r.get("overlap_comparison_status") == "MATERIAL_CONFLICT"}
    session_date_set = set(sessions)
    calendar_hash = sha(CAL)
    price_hash = sha(PRICE)
    feature_time_rows = read_csv(FEATURE_TIME)
    feature_time_status_counts = {}
    for r in feature_time_rows:
        key = (r.get("feature_code", ""), r.get("row_check_reason", ""), r.get("strict_pit_status", ""))
        feature_time_status_counts["|".join(key)] = feature_time_status_counts.get("|".join(key), 0) + 1

    out_rows = []
    price_lineage_rows = []
    for origin_row in load_origin_rows():
        origin = date.fromisoformat(origin_row["forecast_origin_date"])
        cutoff = friday_cutoff(origin)
        # All candidate closes, no post-cutoff dates, with the new explicit price proxy.
        eligible = []
        for d in sessions:
            if d >= origin.isoformat() or d not in prices:
                continue
            obs = date.fromisoformat(d)
            avail = proxy_price_available_at(obs)
            if avail <= cutoff:
                eligible.append((d, avail))
        p0_date = eligible[-1][0] if eligible else ""
        p0_row = prices.get(p0_date, {})
        target, target_type, target_evidence = target_session(origin, calendar, price_dates)
        trow = prices.get(target, {})
        y = ""
        if p0_row.get("index_level") and trow.get("index_level"):
            p0v, tv = float(p0_row["index_level"]), float(trow["index_level"])
            if p0v > 0:
                y = tv / p0v - 1
        prior_sessions = [d for d in sessions if d <= p0_date]
        window_dates = prior_sessions[-21:]
        window_prices = [float(prices[d]["index_level"]) for d in window_dates if d in prices and prices[d].get("index_level")]
        for j, wd in enumerate(window_dates):
            pr = prices.get(wd, {})
            price_lineage_rows.append({"forecast_origin_id": origin_row["forecast_origin_id"],
                "forecast_origin_date": origin.isoformat(), "forecast_cutoff_utc": cutoff.isoformat(),
                "window_position_0_oldest_20_latest": j, "observation_date": wd,
                "index_level_candidate": pr.get("index_level", ""), "source": pr.get("adopted_source", ""),
                "source_file_sha256": pr.get("source_file_sha256", ""),
                "proxy_available_at_utc": proxy_price_available_at(date.fromisoformat(wd)).isoformat(),
                "calendar_class_candidate": calendar.get(wd, {}).get("classification", "MISSING"),
                "calendar_evidence_status": calendar.get(wd, {}).get("evidence_status", "UNKNOWN"),
                "is_p0": "YES" if wd == p0_date else "NO",
                "used_as_ret5_endpoint": "YES" if j in (15, 20) else "NO",
                "used_as_ret20_endpoint": "YES" if j in (0, 20) else "NO",
                "used_for_rv20_return_window": "YES" if 0 <= j <= 20 else "NO",
                "source_conflict_id": pr.get("conflict_id", ""),
                "source_conflict_status": pr.get("overlap_comparison_status", "")})
        feats = rolling_values(window_prices)
        conflict_window = sorted(set(window_dates) & conflict_dates)
        direct_conflict = bool({p0_date, target} & conflict_dates)
        if conflict_window or direct_conflict:
            feature_status = "ISOLATED_2019_PRICE_CONFLICT"
            feats = {}
        elif len(window_prices) != 21:
            feature_status = "BLOCKED_INCOMPLETE_21_PRICE_WINDOW"
            feats = {}
        else:
            feature_status = "CANDIDATE_VALUES_RULE_CALENDAR_COMPLETENESS_UNKNOWN"
        session_span = sum(1 for d in sessions if p0_date < d <= target) if p0_date and target else ""
        label_avail = proxy_price_available_at(date.fromisoformat(target)).isoformat() if target in prices else ""
        calendar_gate = "UNKNOWN_RULE_GENERATED_CALENDAR_COMPLETENESS"
        if target_type == "UNKNOWN":
            calendar_gate = "BLOCKED_TARGET_SESSION_UNKNOWN"
        source_gate = "BLOCKED_SOURCE_SPECIFIC_NONPRICE_AVAILABILITY_RULE_NOT_FROZEN"
        price_gate = "CANDIDATE_PRICE_VERSION_NOT_OFFICIAL_POINTWISE_VERIFIED"
        if conflict_window or direct_conflict:
            price_gate = "ISOLATED_PRICE_CONFLICT"
        out_rows.append({
            "forecast_origin_id": origin_row["forecast_origin_id"], "period": origin_row["period"],
            "forecast_origin_date": origin.isoformat(), "forecast_cutoff_utc": cutoff.isoformat(),
            "p0_date_candidate": p0_date, "p0_candidate": p0_row.get("index_level", ""),
            "p0_source": p0_row.get("adopted_source", ""), "p0_source_file_sha256": p0_row.get("source_file_sha256", ""),
            "p0_available_at_proxy_utc": eligible[-1][1].isoformat() if eligible else "",
            "p0_proxy_rule": "NEXT_NY_NATURAL_DAY_00_00", "target_nominal_date": (origin + timedelta(days=7)).isoformat(),
            "target_date_candidate": target, "target_session_type_candidate": target_type,
            "target_calendar_evidence": target_evidence, "actual_price_candidate": trow.get("index_level", ""),
            "target_source": trow.get("adopted_source", ""), "target_source_file_sha256": trow.get("source_file_sha256", ""),
            "forward_simple_return_candidate": "" if y == "" else format(y, ".16g"),
            "label_available_at_proxy_utc": label_avail,
            "label_matured_by_forecast_cutoff_proxy": ("YES" if label_avail and datetime.fromisoformat(label_avail) <= cutoff else "NO" if label_avail else "UNKNOWN"),
            "calendar_session_span_candidate": session_span,
            "calendar_status": calendar_gate, "price_version_status": price_gate,
            "RET5_candidate": feats.get("RET5", ""), "RET20_candidate": feats.get("RET20", ""),
            "RV20_candidate": feats.get("RV20", ""), "price_feature_status": feature_status,
            "price_feature_window_first": window_dates[0] if window_dates else "",
            "price_feature_window_last": window_dates[-1] if window_dates else "",
            "price_feature_window_session_count_proxy": len(window_dates),
            "conflict_dates_in_price_window": "|".join(conflict_window),
            "nonprice_features_status": source_gate,
            "VIX_value": "", "VIX_observation_date": "UNKNOWN", "VIX_available_at": "UNKNOWN",
            "UST10Y_value": "", "UST10Y_observation_date": "UNKNOWN", "UST10Y_available_at": "UNKNOWN",
            "UST3M_value": "", "UST3M_observation_date": "UNKNOWN", "UST3M_available_at": "UNKNOWN",
            "UST10Y_MINUS_UST2Y_value": "", "UST10Y_MINUS_UST2Y_observation_date": "UNKNOWN", "UST10Y_MINUS_UST2Y_available_at": "UNKNOWN",
            "strict_pit_status": "UNKNOWN", "research_admission_status": "BLOCKED_PENDING_CALENDAR_AND_SOURCE_SPECIFIC_AVAILABILITY"
        })

    write_csv(OUT / "corrected_xy_candidate_preflight.csv", out_rows)
    write_csv(OUT / "price_feature_input_lineage.csv", price_lineage_rows)
    g3rows = [r for r in out_rows if r["period"] == "G3_DEVELOPMENT"]
    g4rows = [r for r in out_rows if r["period"].startswith("G4_")]

    # Compare date mechanics only; old and new values are never combined for scoring.
    old_by_date = {}
    for path in (G3, G4):
        for r in read_csv(path):
            old_by_date.setdefault(r["forecast_origin_date"], r)
    old_g2_by_date = {r["forecast_date"]: r for r in read_csv(OLD_G2)}
    delta_rows = []
    for r in out_rows:
        old = old_by_date.get(r["forecast_origin_date"], {})
        old_g2 = old_g2_by_date.get(r["forecast_origin_date"], {})
        old_p0 = old.get("p0_date", old_g2.get("P0_observation_date", ""))
        old_target = old.get("target_date", old.get("target_candidate", ""))
        new_p0 = r["p0_date_candidate"]
        p0_days = (date.fromisoformat(new_p0) - date.fromisoformat(old_p0)).days if old_p0 and new_p0 else ""
        session_pos = {d: i for i, d in enumerate(sessions)}
        p0_shift_sessions = session_pos[new_p0] - session_pos[old_p0] if new_p0 in session_pos and old_p0 in session_pos else ""
        old_span = sum(1 for d in sessions if old_p0 < d <= old_target) if old_p0 and old_target else ""
        new_span = r["calendar_session_span_candidate"]
        old_p0_value = old.get("p0", old_g2.get("P0", ""))
        old_target_value = old.get("actual_price", old.get("actual_price_candidate", old_g2.get("target_price", "")))
        old_return = old.get("actual_return", old.get("actual_return_candidate", old_g2.get("Y_simple_return_candidate", "")))
        new_return = r["forward_simple_return_candidate"]
        return_delta = float(new_return) - float(old_return) if new_return and old_return else ""
        delta_rows.append({"forecast_origin_id": r["forecast_origin_id"], "period": r["period"],
                           "forecast_origin_date": r["forecast_origin_date"], "old_p0_date": old_p0,
                           "old_p0_candidate": old_p0_value, "new_p0_date_candidate": new_p0,
                           "new_p0_candidate": r["p0_candidate"], "p0_calendar_day_shift": p0_days,
                           "p0_session_shift_in_rule_calendar": p0_shift_sessions,
                           "old_target_date": old_target, "new_target_date_candidate": r["target_date_candidate"],
                           "old_target_price_candidate": old_target_value, "new_target_price_candidate": r["actual_price_candidate"],
                           "old_return_candidate": old_return, "new_return_candidate": new_return,
                           "return_delta_new_minus_old": return_delta,
                           "target_date_changed": "YES" if old_target and old_target != r["target_date_candidate"] else "NO" if old_target else "UNKNOWN",
                           "old_horizon_session_count_in_rule_calendar": old_span,
                           "new_horizon_session_count_in_rule_calendar": new_span,
                           "calendar_completeness": "UNKNOWN_RULE_GENERATED_PARTIAL_OFFICIAL_CROSSCHECK"})
    write_csv(OUT / "origin_rule_delta.csv", delta_rows)

    calendar_evidence_by_origin = {r["forecast_date"]: r for r in read_csv(CAL_EVIDENCE)}
    target_review = []
    for r in out_rows:
        ev = calendar_evidence_by_origin.get(r["forecast_origin_date"], {})
        nominal = r["target_nominal_date"]
        tcls = calendar.get(r["target_date_candidate"], {}).get("classification", "MISSING")
        if ev.get("calendar_adjudication_status") == "PASS_SCHEDULED_SESSION_PLUS_VENDOR_OBSERVATION":
            evid = "TARGET_EXCEPTION_SCHEDULE_AND_VENDOR_ROW_CROSS_SUPPORT; ACTUAL_SESSION_COMPLETENESS_UNKNOWN"
        elif ev.get("calendar_adjudication_status") == "PENDING_EVIDENCE":
            evid = "TARGET_EXCEPTION_PENDING_EVIDENCE"
        else:
            evid = "RULE_GENERATED_CALENDAR_AND_VENDOR_ROW_ONLY; COMPLETENESS_UNKNOWN"
        target_review.append({"forecast_origin_id": r["forecast_origin_id"], "forecast_origin_date": r["forecast_origin_date"],
                              "nominal_target_friday": nominal, "nominal_calendar_class": calendar.get(nominal, {}).get("classification", "MISSING"),
                              "candidate_target_date": r["target_date_candidate"], "candidate_target_calendar_class": tcls,
                              "target_source_row_present": "YES" if r["actual_price_candidate"] else "NO",
                              "stage2c_calendar_exception_status": ev.get("calendar_adjudication_status", "NO_ROW"),
                              "stage2c_target_session_type": ev.get("target_session_type", ""),
                              "stage2c_target_evidence_url": ev.get("target_session_evidence_url", ""),
                              "evidence_summary": evid, "admission_status": "UNKNOWN_NOT_CALENDAR_ADMITTED"})
    write_csv(OUT / "target_session_review.csv", target_review)

    annual_calendar = []
    years = sorted({d[:4] for d in calendar if "2010" <= d[:4] <= "2025"})
    for year in years:
        ysessions = {d for d in sessions if d.startswith(year)}
        yprices = {d for d in price_dates if d.startswith(year)}
        annual_calendar.append({"year": year, "rule_calendar_sessions_full_or_early": len(ysessions),
                                "candidate_price_observation_dates": len(yprices),
                                "calendar_session_without_price": len(ysessions - yprices),
                                "price_date_not_full_or_early_calendar": len(yprices - ysessions),
                                "calendar_evidence_status": "RULE_GENERATED_PARTIAL_OFFICIAL_CROSSCHECK_COMPLETENESS_UNKNOWN"})
    write_csv(OUT / "calendar_price_coverage.csv", annual_calendar)

    feature_rows = []
    feature_counts = {}
    for r in feature_time_rows:
        feature_counts[r.get("feature_code", "")] = feature_counts.get(r.get("feature_code", ""), 0) + 1
    for code, source, filepaths in [
        ("VIX", "Cboe VIX daily close", [RAW_VIX]),
        ("UST10Y", "US Treasury daily yield curve 10 Yr", RAW_TREASURY),
        ("UST3M", "US Treasury daily yield curve 3 Mo", RAW_TREASURY),
        ("UST2Y", "US Treasury daily yield curve 2 Yr", RAW_TREASURY)]:
        for p in filepaths:
            feature_rows.append({"feature_code": code, "source_definition": source,
                                 "source_file": str(p.relative_to(ROOT)), "source_file_sha256": sha(p) if p.exists() else "MISSING",
                                 "old_g3_source_time_rows": feature_counts.get(code, 0),
                                 "old_lineage_availability_rule": "INHERITED_OLD_PROXY_NEXT_NYSE_SESSION_23_59_59; NOT SOURCE_SPECIFIC",
                                 "new_source_specific_proxy_rule": "NOT_FOUND_OR_NOT_FROZEN",
                                 "release_timestamp": "UNKNOWN", "vintage_revisions": "UNKNOWN",
                                 "corrected_feature_admission": "BLOCKED"})
    write_csv(OUT / "source_availability_gate.csv", feature_rows)

    # Candidate historical labels for maturity accounting, using the same explicit
    # price proxy and candidate calendar. Counts are not training authorization.
    all_sched = [r for r in read_csv(STAGE2C_SCHEDULE)
                 if r["forecast_origin_date"] <= max(x["forecast_origin_date"] for x in out_rows)]
    labels = []
    for s in all_sched:
        od = date.fromisoformat(s["forecast_origin_date"])
        cut = friday_cutoff(od)
        elig = [(d, proxy_price_available_at(date.fromisoformat(d))) for d in sessions
                if d < od.isoformat() and d in prices and proxy_price_available_at(date.fromisoformat(d)) <= cut]
        if not elig:
            continue
        pdate = elig[-1][0]
        tgt, ttype, _ = target_session(od, calendar, price_dates)
        if ttype == "UNKNOWN" or pdate not in prices or tgt not in prices:
            continue
        prev = [d for d in sessions if d <= pdate]
        wd = prev[-21:]
        if len(wd) != 21 or any(d not in prices or not prices[d].get("index_level") for d in wd):
            continue
        if set(wd) & conflict_dates or pdate in conflict_dates or tgt in conflict_dates:
            continue
        la = proxy_price_available_at(date.fromisoformat(tgt))
        labels.append({"forecast_origin_date": od.isoformat(), "target_date_candidate": tgt,
                       "label_available_at_proxy_utc": la.isoformat(), "price_window_complete_candidate": "YES",
                       "calendar_status": "UNKNOWN_RULE_GENERATED_COMPLETENESS"})
    maturity_rows = []
    for outer in out_rows:
        cut = datetime.fromisoformat(outer["forecast_cutoff_utc"])
        mature = [l for l in labels if l["forecast_origin_date"] < outer["forecast_origin_date"]
                  and datetime.fromisoformat(l["label_available_at_proxy_utc"]) <= cut]
        maturity_rows.append({"forecast_origin_id": outer["forecast_origin_id"], "period": outer["period"],
                              "forecast_cutoff_utc": outer["forecast_cutoff_utc"],
                              "candidate_matured_price_label_count": len(mature),
                              "first_matured_origin_date": mature[0]["forecast_origin_date"] if mature else "",
                              "last_matured_origin_date": mature[-1]["forecast_origin_date"] if mature else "",
                              "max_label_available_at_proxy_utc": max((x["label_available_at_proxy_utc"] for x in mature), default=""),
                              "calendar_and_actual_release_status": "UNKNOWN_NOT_AUTHORIZED_AS_TRAINING_MEMBERSHIP"})
    write_csv(OUT / "candidate_training_label_maturity.csv", maturity_rows)

    gate_models = [
        ("MYSELF", "Ridge", "RET5|RET20|RV20|VIX|UST10Y|UST3M|UST10Y_MINUS_UST2Y", "BLOCKED_NONPRICE_SOURCE_RULE_AND_CALENDAR"),
        ("DMC", "Ridge", "VIX|UST10Y", "BLOCKED_VIX_AND_TREASURY_SOURCE_RULE_AND_CALENDAR"),
        ("TLJ", "OLS", "RV20", "BLOCKED_PRICE_CALENDAR_COMPLETENESS_AND_2019_WINDOW_ISOLATION"),
        ("EVA", "OLS", "UST10Y", "BLOCKED_TREASURY_SOURCE_RULE_AND_CALENDAR")]
    model_gate_rows = []
    for period, rows in (("G3", g3rows), ("G4", g4rows)):
        for member, model, feats, reason in gate_models:
            available_rows = 0
            for row in rows:
                source_status = "UNKNOWN" if member != "TLJ" else "PASS"
                admissible = model_row_admissible(
                    feature_available_at=row["p0_available_at_proxy_utc"],
                    cutoff_utc=row["forecast_cutoff_utc"],
                    calendar_status="PASS" if row["calendar_status"] == "PASS" else "UNKNOWN",
                    source_rule_status=source_status,
                    conflict_isolated=row["price_feature_status"] == "ISOLATED_2019_PRICE_CONFLICT")
                if admissible:
                    available_rows += 1
            model_gate_rows.append({"period": period, "member": member, "model": model,
                                    "features": feats, "candidate_origins": len(rows),
                                    "model_ready_origins": available_rows, "status": "BLOCKED" if available_rows < len(rows) else "READY_FOR_REVIEW",
                                    "blocking_reason": reason,
                                    "strict_pit_status": "UNKNOWN"})
    write_csv(OUT / "model_input_gate.csv", model_gate_rows)
    gate_rows = []
    for period, rows in (("G3", g3rows), ("G4", g4rows)):
        numeric_xy = [r for r in rows if r["p0_candidate"] and r["actual_price_candidate"] and r["forward_simple_return_candidate"]]
        gate_rows.append({"period": period, "candidate_origins": len(rows), "candidate_price_xy_rows": len(numeric_xy),
                          "calendar_admitted_rows": 0, "source_specific_nonprice_admitted_rows": 0,
                          "four_model_common_admitted_rows": 0,
                          "calendar_unknown_rows": sum(r["calendar_status"].startswith("UNKNOWN") for r in rows),
                          "price_conflict_isolated_rows": sum(r["price_feature_status"] == "ISOLATED_2019_PRICE_CONFLICT" for r in rows),
                          "strict_pit_verified_rows": 0, "period_status": "BLOCKED_NOT_MODEL_READY"})
    write_csv(OUT / "period_gate_counts.csv", gate_rows)
    input_manifest = []
    for p in input_paths:
        input_manifest.append({"path": str(p.relative_to(ROOT)), "sha256": sha(p), "bytes": p.stat().st_size})
    (OUT / "input_manifest.json").write_text(json.dumps({"protocol_sha256": protocol_sha,
        "input_files": input_manifest, "price_reference_candidate_sha256": price_hash,
        "calendar_candidate_sha256": calendar_hash,
        "feature_time_audit_rows": len(feature_time_rows),
        "feature_time_audit_status_counts": feature_time_status_counts,
        "strict_pit": "UNKNOWN", "model_run": "NOT_RUN_GATE_BLOCKED"}, indent=2)+"\n", encoding="utf-8")
    return {"rows": len(out_rows), "g3": len(g3rows), "g4": len(g4rows), "price_xy": {x["period"]: x["candidate_price_xy_rows"] for x in gate_rows},
            "gate_counts": gate_rows, "source_rows": len(feature_time_rows), "candidate_labels_for_maturity": len(labels)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
