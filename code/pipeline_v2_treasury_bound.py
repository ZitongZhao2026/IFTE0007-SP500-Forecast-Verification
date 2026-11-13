/opt/homebrew/Library/Homebrew/cmd/shellenv.sh: line 27: /bin/ps: Operation not permitted
#!/usr/bin/env python3
"""Fail-closed corrected-proxy/live-input pipeline primitives.

This module does not authorize a forecast. It keeps strict PIT UNKNOWN even when
the live cutoff checks pass because the historical training set is proxy based.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
MODELS = {
    "SEVEN_FACTOR_RIDGE": ["RET5", "RET20", "RV20", "VIX", "UST10Y", "UST3M", "SPREAD"],
    "VIX_UST10Y_RIDGE": ["VIX", "UST10Y"],
}
TRAINING_FEATURES = MODELS["SEVEN_FACTOR_RIDGE"]
PROTOCOL_SHA = "b80853fb0fa9135d58cf4e3d0c308bc11e354db6ade78b90dadf51814f71b706"
NY = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_utc(value: str, label: str) -> datetime:
    if not value or value == "UNKNOWN":
        raise ValueError(f"{label}: timestamp missing/UNKNOWN")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label}: invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label}: timezone required")
    return parsed.astimezone(timezone.utc)


def proxy_available_at(source: str, observation_date: str) -> datetime:
    """Calculate, never infer from the CSV, the approved research proxy time."""
    obs = date.fromisoformat(observation_date)
    if source == "SPX_PRICE":
        local = datetime.combine(obs + timedelta(days=1), time.min, NY)
    elif source in {"CBOE_VIX", "US_TREASURY_10Y", "US_TREASURY_3M", "US_TREASURY_2Y", "US_TREASURY_CURVE"}:
        local = datetime.combine(obs + timedelta(days=2), time(23, 59, 59), NY)
    else:
        raise ValueError(f"unregistered source: {source}")
    return local.astimezone(timezone.utc)


def verify_corrected_rules(rules_path: Path, protocol_path: Path) -> dict:
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    if sha256(protocol_path) != PROTOCOL_SHA or rules.get("protocol_sha256") != PROTOCOL_SHA:
        raise ValueError("protocol SHA-256 mismatch")
    required = {
        "mode": "EXPLORATORY_CORRECTED_PROXY_PIT",
        "forecast": "Friday 12:00 Europe/London",
        "price_proxy": "next New York natural day 00:00",
        "nonprice_proxy": "two New York natural days after observation at 23:59:59",
        "strict_pit": "UNKNOWN",
    }
    for key, value in required.items():
        if rules.get(key) != value:
            raise ValueError(f"corrected policy mismatch: {key}")
    return rules


def verify_proxy_row(source: str, observation_date: str, recorded_proxy_utc: str,
                     cutoff_utc: str) -> datetime:
    expected = proxy_available_at(source, observation_date)
    recorded = parse_utc(recorded_proxy_utc, f"{source} proxy time")
    if recorded != expected:
        raise ValueError(f"{source} proxy timestamp does not match frozen rule")
    cutoff = parse_utc(cutoff_utc, "forecast cutoff")
    if recorded > cutoff:
        raise ValueError(f"{source} observation is unavailable by cutoff under proxy rule")
    return expected


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv_new(path: Path, rows: list[dict[str, str]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    if not rows:
        raise ValueError("refusing to write empty audit snapshot")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def finite(value: str, label: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: missing/non-numeric") from exc
    if not math.isfinite(x):
        raise ValueError(f"{label}: non-finite")
    return x


def verify_source_inventory(inventory_path: Path, root: Path) -> list[dict[str, str]]:
    items = read_csv(inventory_path)
    if not items:
        raise ValueError("empty source hash inventory")
    for item in items:
        path = (root / item["path"]).resolve()
        if not path.is_file() or sha256(path) != item.get("sha256"):
            raise ValueError(f"source hash mismatch/missing: {item.get('path')}")
    return items


def _price_window(lineage: list[dict[str, str]], row: dict[str, str]) -> list[dict[str, str]]:
    related = [x for x in lineage if x.get("forecast_origin_id") == row["forecast_origin_id"]]
    related.sort(key=lambda x: int(x["position"]))
    if len(related) != 21 or [int(x["position"]) for x in related] != list(range(21)):
        raise ValueError("price lineage is not a complete 21-observation window")
    if related[0]["observation_date"] != row["price_window_start"] or related[-1]["observation_date"] != row["price_window_end"]:
        raise ValueError("price lineage bounds differ from candidate row")
    if any(x.get("conflict") == "YES" for x in related):
        raise ValueError("known price conflict intersects training feature window")
    values = [finite(x["price"], "price lineage") for x in related]
    if any(x <= 0 for x in values):
        raise ValueError("nonpositive price in rolling window")
    return related


def _reference_price_map(reference_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result = {}
    for item in reference_rows:
        day = item.get("observation_date", "")
        if not day or day in result:
            raise ValueError("reference price index has missing/duplicate observation dates")
        value = finite(item.get("index_level", ""), "reference index level")
        if value <= 0:
            raise ValueError("reference price index contains nonpositive value")
        result[day] = item
    if not result:
        raise ValueError("empty common reference price index")
    return result


def _calendar_map(calendar_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result = {}
    for item in calendar_rows:
        day = item.get("date", "")
        if not day or day in result:
            raise ValueError("candidate SPX calendar has missing/duplicate dates")
        result[day] = item
    if not result:
        raise ValueError("empty candidate SPX calendar")
    return result


def _expected_target_date(forecast_date: str, calendar: dict[str, dict[str, str]]) -> tuple[str, str]:
    origin = date.fromisoformat(forecast_date)
    nominal = origin + timedelta(days=7)
    if origin.weekday() != 4 or nominal.weekday() != 4:
        raise ValueError("forecast date is not a Friday")
    nominal_row = calendar.get(nominal.isoformat())
    if nominal_row is None:
        raise ValueError("next-Friday target missing from candidate calendar")
    if nominal_row.get("classification") in {"FULL", "EARLY"}:
        return nominal.isoformat(), "RULE_CALENDAR_TARGET_MATCH_ACTUAL_SESSION_UNKNOWN"
    if not str(nominal_row.get("classification", "")).startswith("CLOSED_"):
        raise ValueError("next-Friday target calendar status is unrecognized")
    start = nominal - timedelta(days=4)
    candidates = [d for d, item in calendar.items()
                  if start <= date.fromisoformat(d) < nominal
                  and item.get("classification") in {"FULL", "EARLY"}]
    if not candidates:
        raise ValueError("no candidate preceding session in target week")
    return max(candidates), "RULE_CALENDAR_FALLBACK_ACTUAL_SESSION_UNKNOWN"


def _verify_raw_record(row: dict[str, str], evidence_root: Path) -> None:
    """Bind a live value to exactly one row in its hashed raw source file."""
    if row.get("source_provider") == "YAHOO_FINANCE":
        _verify_yahoo_raw_record(row, evidence_root)
        return
    if Path(row.get("source_file_path", "")).suffix.lower() == ".json":
        raise ValueError("unregistered live JSON source")
    date_field, value_field = row.get("raw_date_field", ""), row.get("raw_value_field", "")
    if not date_field or not value_field:
        raise ValueError("live row lacks raw date/value field mapping")
    raw_path = (evidence_root / row["source_file_path"]).resolve()
    matches = []
    with raw_path.open(newline="", encoding="utf-8-sig") as handle:
        for source_row in csv.DictReader(handle):
            raw_date = source_row.get(date_field, "").strip()
            # The official Cboe and Treasury CSVs use month/day/year, while
            # FRED SP500 uses ISO dates. Never rely on locale or guess order.
            formats = ("%Y-%m-%d",) if row.get("source") == "SPX_PRICE" else ("%m/%d/%Y", "%Y-%m-%d")
            parsed_date = None
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(raw_date, fmt).date().isoformat()
                    break
                except ValueError:
                    continue
            if parsed_date is None:
                raise ValueError(f"invalid {row.get('source')} raw date in {date_field}: {raw_date!r}")
            if parsed_date != row["observation_date"]:
                continue
            version_field = row.get("raw_version_field", "")
            if version_field and source_row.get(version_field, "").strip() != row.get("source_version", ""):
                continue
            raw_value = finite(source_row.get(value_field, ""), f"raw {value_field}")
            expected_value = finite(row["value"], row["feature_code"])
            if math.isclose(raw_value, expected_value, rel_tol=0.0, abs_tol=1e-12):
                matches.append(source_row)
    if len(matches) != 1:
        raise ValueError("live value/date/version does not identify exactly one record in the hashed raw source")


def _verify_yahoo_raw_record(row: dict[str, str], evidence_root: Path) -> None:
    """Bind one ^GSPC daily Close to the hashed Yahoo Chart JSON, never Adj Close."""
    if row.get("source") != "SPX_PRICE" or row.get("feature_code") != "SPX_PRICE":
        raise ValueError("Yahoo source is only registered for SPX price observations")
    if (row.get("raw_date_field"), row.get("raw_value_field")) != (
        "chart.result[0].timestamp@America/New_York", "chart.result[0].indicators.quote[0].close"):
        raise ValueError("Yahoo raw date/Close mapping is not the frozen ^GSPC mapping")
    if row.get("raw_version_field", ""):
        raise ValueError("Yahoo source version must bind to the entire raw JSON hash")
    if row.get("source_version") != "YAHOO_CHART_1D_SHA256_" + row.get("source_file_sha256", ""):
        raise ValueError("Yahoo source version does not bind the raw JSON hash")
    raw_path = (evidence_root / row["source_file_path"]).resolve()
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    chart = payload.get("chart", {})
    results = chart.get("result")
    if chart.get("error") is not None or not isinstance(results, list) or len(results) != 1:
        raise ValueError("Yahoo JSON has no unique chart result")
    result = results[0]
    meta = result.get("meta", {})
    if (meta.get("symbol"), meta.get("instrumentType"), meta.get("currency"),
        meta.get("exchangeTimezoneName"), meta.get("dataGranularity")) != (
        "^GSPC", "INDEX", "USD", "America/New_York", "1d"):
        raise ValueError("Yahoo JSON symbol/index/timezone/granularity mismatch")
    timestamps = result.get("timestamp")
    quotes = result.get("indicators", {}).get("quote")
    if not isinstance(timestamps, list) or not isinstance(quotes, list) or len(quotes) != 1:
        raise ValueError("Yahoo JSON daily timestamps or quote array missing")
    closes = quotes[0].get("close")
    if not isinstance(closes, list) or len(timestamps) != len(closes) or not timestamps:
        raise ValueError("Yahoo JSON timestamp/Close array length mismatch")
    seen = {}
    for timestamp, close_value in zip(timestamps, closes):
        if isinstance(timestamp, bool) or not isinstance(timestamp, int):
            raise ValueError("Yahoo JSON timestamp is not an integer epoch second")
        session_date = datetime.fromtimestamp(timestamp, timezone.utc).astimezone(NY).date().isoformat()
        if session_date in seen:
            raise ValueError("Yahoo JSON has duplicate New York observation dates")
        if close_value is None:
            raise ValueError("Yahoo JSON has a missing Close in the captured window")
        try:
            cents = Decimal(str(close_value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Yahoo JSON has an invalid Close") from exc
        if not cents.is_finite() or cents <= 0:
            raise ValueError("Yahoo JSON Close is nonpositive/non-finite")
        seen[session_date] = cents
    observation = row["observation_date"]
    if observation not in seen:
        raise ValueError("Yahoo JSON does not contain the requested observation date")
    try:
        declared = Decimal(str(row["value"]))
    except InvalidOperation as exc:
        raise ValueError("Yahoo declared Close is not numeric") from exc
    if not declared.is_finite() or declared != seen[observation]:
        raise ValueError("Yahoo declared Close does not match the raw daily Close at two index decimals")


def _verify_yahoo_capture_and_source_approval(row: dict[str, str], evidence_root: Path,
                                              cutoff: datetime) -> None:
    """Require a capture binding and separate human source-change approval."""
    required = ("source_capture_path", "source_capture_sha256", "source_url",
                "source_provider_approval_record_path", "source_provider_approval_record_sha256")
    if any(not row.get(key) for key in required):
        raise ValueError("Yahoo source lacks capture metadata or separate provider approval")
    capture_path = (evidence_root / row["source_capture_path"]).resolve()
    if not capture_path.is_file() or sha256(capture_path) != row["source_capture_sha256"]:
        raise ValueError("Yahoo capture metadata missing or hash mismatch")
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    raw_path = (evidence_root / row["source_file_path"]).resolve()
    if (capture.get("source_id") != "yahoo_gspc" or
        Path(capture.get("raw_path", "")).resolve() != raw_path or
        capture.get("raw_sha256") != row["source_file_sha256"] or
        capture.get("requested_url") != row["source_url"] or
        capture.get("pit_admission") != "NOT_REVIEWED"):
        raise ValueError("Yahoo capture metadata is not bound to the original JSON/URL")
    url = urlsplit(row["source_url"])
    query = parse_qs(url.query)
    if (url.scheme, url.hostname, url.path, query.get("interval")) != (
        "https", "query1.finance.yahoo.com", "/v8/finance/chart/%5EGSPC", ["1d"]):
        raise ValueError("Yahoo URL is not the registered ^GSPC daily Chart request")
    if urlsplit(capture.get("response_url", "")).hostname != "query1.finance.yahoo.com":
        raise ValueError("Yahoo capture redirected to an unexpected provider")
    started = parse_utc(capture.get("retrieval_started_utc", ""), "Yahoo capture start")
    finished = parse_utc(capture.get("retrieval_finished_utc", ""), "Yahoo capture finish")
    if (started > finished or finished > cutoff or
        finished != parse_utc(row["retrieval_timestamp_utc"], "Yahoo retrieval") or
        finished != parse_utc(row["available_at_utc"], "Yahoo evidenced availability")):
        raise ValueError("Yahoo capture was not completed and bound before the forecast cutoff")
    if row["evidence_type"] == "PRE_CUTOFF_ARCHIVE_CAPTURE" and (
        (evidence_root / row["evidence_path"]).resolve() != capture_path or
        row["evidence_sha256"] != row["source_capture_sha256"]):
        raise ValueError("Yahoo pre-cutoff availability evidence must be the original capture metadata")
    approval_path = (evidence_root / row["source_provider_approval_record_path"]).resolve()
    if not approval_path.is_file() or sha256(approval_path) != row["source_provider_approval_record_sha256"]:
        raise ValueError("Yahoo source-change approval record missing or hash mismatch")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    expected = {"scope": "LIVE_PRICE_SOURCE_CHANGE", "decision": "approved",
                "source_provider": "YAHOO_FINANCE", "forecast_cutoff_utc": cutoff.isoformat(),
                "raw_sha256": row["source_file_sha256"], "capture_sha256": row["source_capture_sha256"],
                "source_version": row["source_version"]}
    if any(approval.get(key) != value for key, value in expected.items()) or not approval.get("decision_reference"):
        raise ValueError("Yahoo source-change approval does not bind this capture/cutoff/version")
    log_hash = approval.get("approval_log_record_sha256", "")
    if len(log_hash) != 64:
        raise ValueError("Yahoo source approval lacks governance log binding")
    log_path = ROOT / "governance/approval_log.jsonl"
    if not log_path.is_file():
        raise ValueError("governance approval log missing")
    if not any(hashlib.sha256(line).hexdigest() == log_hash and
               all(json.loads(line).get(key) == value for key, value in {**expected,
                   "decision_reference": approval["decision_reference"]}.items())
               for line in log_path.read_bytes().splitlines()):
        raise ValueError("Yahoo source approval has no matching exact governance decision")


def _verify_official_pre_cutoff_capture(row: dict[str, str], evidence_root: Path,
                                       cutoff: datetime) -> None:
    """Check a Cboe/Treasury capture as evidence of availability, not first release."""
    expected = {
        "CBOE_VIX": ("cboe_vix", "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"),
        "US_TREASURY_CURVE": ("treasury_2026", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all?_format=csv&field_tdr_date_value=2026&page=&type=daily_treasury_yield_curve"),
    }
    if row.get("source") not in expected or row.get("release_timestamp_utc") != "UNKNOWN":
        raise ValueError("official capture exemption is limited to Cboe/Treasury with UNKNOWN first release")
    for key in ("source_capture_path", "source_capture_sha256", "source_url"):
        if not row.get(key):
            raise ValueError(f"official capture lacks {key}")
    capture_path = (evidence_root / row["source_capture_path"]).resolve()
    if not capture_path.is_file() or sha256(capture_path) != row["source_capture_sha256"]:
        raise ValueError("official capture metadata missing or hash mismatch")
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    source_id, official_url = expected[row["source"]]
    source_path = (evidence_root / row["source_file_path"]).resolve()
    if (row["source_url"] != official_url or capture.get("source_id") != source_id or
        capture.get("requested_url") != official_url or capture.get("response_url") != official_url or
        capture.get("http_status") != 200 or capture.get("pit_admission") != "NOT_REVIEWED" or
        Path(capture.get("raw_path", "")).resolve() != source_path or
        capture.get("raw_sha256") != row["source_file_sha256"] or
        (evidence_root / row["evidence_path"]).resolve() != capture_path or
        row["evidence_sha256"] != row["source_capture_sha256"]):
        raise ValueError("official capture is not bound to its source URL/raw file/evidence")
    started = parse_utc(capture.get("retrieval_started_utc", ""), "official capture start")
    finished = parse_utc(capture.get("retrieval_finished_utc", ""), "official capture finish")
    if (started > finished or finished > cutoff or
        finished != parse_utc(row["retrieval_timestamp_utc"], "official retrieval") or
        finished != parse_utc(row["available_at_utc"], "official evidenced availability")):
        raise ValueError("official observation was not captured and bound before cutoff")


def _session_completed_by(item: dict[str, str], calendar_id: str, cutoff: datetime) -> datetime | None:
    """Return an evidenced completion bound, never an invented Treasury close."""
    if item.get("calendar_id") != calendar_id:
        return None
    if item.get("session_status") == "VERIFIED":
        return parse_utc(item.get("session_close_utc", ""), f"{calendar_id} session close")
    if (calendar_id == "TREASURY" and item.get("session_date") == "2026-11-12"
            and item.get("session_status") == "VERIFIED_AVAILABLE_BY"
            and item.get("session_close_utc", "") in ("", "UNKNOWN")
            and item.get("actual_session_close_utc") == "UNKNOWN"):
        bound = parse_utc(item.get("verified_available_by_utc", ""), "Treasury verified available by")
        if bound > cutoff:
            raise ValueError("Treasury completion bound is after cutoff")
        return bound
    return None


def _latest_verified_session(calendar_rows: list[dict[str, str]], calendar_id: str,
                             cutoff: datetime) -> str:
    sessions = []
    for item in calendar_rows:
        close = _session_completed_by(item, calendar_id, cutoff)
        if close is not None and close <= cutoff:
            sessions.append(item.get("session_date", ""))
    if not sessions:
        raise ValueError(f"no verified completed {calendar_id} session by cutoff")
    return max(sessions)


def validate_candidate_row(row: dict[str, str], lineage: list[dict[str, str]],
                           fit_cutoff_utc: datetime,
                           reference_prices: dict[str, dict[str, str]],
                           candidate_calendar: dict[str, dict[str, str]]) -> str:
    """Re-check corrected source formulas and exact proxies for one weekly row."""
    origin = parse_utc(row["forecast_cutoff_utc"], "row cutoff")
    local = origin.astimezone(LONDON)
    if local.weekday() != 4 or (local.hour, local.minute, local.second) != (12, 0, 0):
        raise ValueError("candidate origin is not Friday 12:00 Europe/London")
    p0 = finite(row["p0"], "P0")
    actual = finite(row["actual_price"], "target price")
    if p0 <= 0 or actual <= 0:
        raise ValueError("candidate prices must be positive")
    if abs(finite(row["return_y"], "Y") - (actual / p0 - 1)) > 1e-12:
        raise ValueError("candidate Y does not match actual/P0 - 1")
    if row["p0_date"] >= row["forecast_date"] or row["target_date"] <= row["forecast_date"]:
        raise ValueError("candidate P0/target chronology is invalid")
    expected_target, target_rule_status = _expected_target_date(row["forecast_date"], candidate_calendar)
    if row["target_date"] != expected_target:
        raise ValueError("candidate target date disagrees with next-Friday/preceding-session rule calendar")
    # Verify that the candidate P0 is the latest price record in the common
    # reference series available under the frozen proxy. Completeness of actual
    # exchange sessions remains UNKNOWN and is not promoted here.
    origin_cutoff = parse_utc(row["forecast_cutoff_utc"], "row cutoff")
    eligible_reference = [day for day in reference_prices
                          if day < row["forecast_date"] and proxy_available_at("SPX_PRICE", day) <= origin_cutoff]
    if not eligible_reference or row["p0_date"] != max(eligible_reference):
        raise ValueError("P0 is not the latest common-reference price available by cutoff")
    reference_p0 = reference_prices[row["p0_date"]]
    if abs(finite(reference_p0["index_level"], "reference P0") - p0) > 1e-9:
        raise ValueError("P0 differs from common reference price candidate")
    if reference_p0.get("conflict_id"):
        raise ValueError("P0 is marked with a known common-reference price conflict")
    reference_target = reference_prices.get(row["target_date"])
    if reference_target is None or abs(finite(reference_target["index_level"], "reference target") - actual) > 1e-9:
        raise ValueError("target price missing/different in common reference candidate")
    if reference_target.get("conflict_id"):
        raise ValueError("target price is marked with a known common-reference conflict")
    window = _price_window(lineage, row)
    calendar_sessions = sorted(day for day, item in candidate_calendar.items()
                               if day <= row["p0_date"] and item.get("classification") in {"FULL", "EARLY"})
    if len(calendar_sessions) < 21 or [x["observation_date"] for x in window] != calendar_sessions[-21:]:
        raise ValueError("price lineage differs from last 21 sessions in rule-generated candidate calendar")
    if any(x.get("calendar_status") != "UNKNOWN_ACTUAL_SESSION" for x in window):
        raise ValueError("price lineage calendar status conflicts with actual-session UNKNOWN policy")
    if row.get("actual_session_evidence") != "UNKNOWN":
        raise ValueError("actual session evidence cannot be upgraded by candidate pipeline")
    verify_proxy_row("SPX_PRICE", row["p0_date"], row["p0_available_proxy_utc"], row["forecast_cutoff_utc"])
    label_at = verify_proxy_row("SPX_PRICE", row["target_date"], row["label_available_proxy_utc"], row["label_available_proxy_utc"])
    if label_at > fit_cutoff_utc:
        raise ValueError("target label is not mature by fit cutoff")
    p = [finite(x["price"], "window price") for x in window]
    if window[-1]["observation_date"] != row["p0_date"] or abs(p[-1] - p0) > 1e-9:
        raise ValueError("P0 does not match final record in corrected price lineage")
    for left, right in zip(window, window[1:]):
        if left["observation_date"] >= right["observation_date"]:
            raise ValueError("price window dates are not strictly increasing")
    computed = {
        "RET5": p[-1] / p[-6] - 1,
        "RET20": p[-1] / p[0] - 1,
    }
    returns = [p[i] / p[i - 1] - 1 for i in range(1, len(p))]
    mean = sum(returns) / 20
    computed["RV20"] = math.sqrt(sum((x - mean) ** 2 for x in returns) / 19)
    for feature in ("RET5", "RET20", "RV20"):
        if abs(finite(row[feature], feature) - computed[feature]) > 1e-12:
            raise ValueError(f"{feature} does not match corrected price lineage")
    for name in ("VIX", "UST10Y", "UST3M", "UST2Y", "SPREAD"):
        source = "CBOE_VIX" if name == "VIX" else "US_TREASURY_CURVE"
        verify_proxy_row(source, row[name + "_date"], row[name + "_available_proxy_utc"], row["forecast_cutoff_utc"])
        finite(row[name], name)
        age = (date.fromisoformat(row["forecast_date"]) - date.fromisoformat(row[name + "_date"])).days
        if age < 0 or age > 5:
            raise ValueError(f"{name} exceeds the approved conservative five-calendar-day staleness cap")
        source_hash = row.get(name + "_source_sha256", "")
        if len(source_hash) != 64 or any(c not in "0123456789abcdef" for c in source_hash.lower()):
            raise ValueError(f"{name} source file SHA-256 missing/invalid")
    if row.get("strict_pit_status") != "STRICT_PIT_UNKNOWN":
        raise ValueError("strict status cannot be promoted from candidate input")
    return target_rule_status


def build_training_candidates(history_path: Path, lineage_path: Path,
                              fit_cutoff_utc: str, model_id: str,
                              reference_prices_path: Path, calendar_path: Path,
                              rejection_rows: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    """Build a non-fitted candidate pool solely from corrected history artifacts."""
    if model_id not in MODELS:
        raise ValueError("unsupported frozen model")
    if "corrected_exploratory_comparison" not in history_path.as_posix():
        raise ValueError("training history must come from corrected exploratory artifacts")
    cutoff = parse_utc(fit_cutoff_utc, "fit cutoff")
    rows = read_csv(history_path)
    lineage = read_csv(lineage_path)
    reference_prices = _reference_price_map(read_csv(reference_prices_path))
    candidate_calendar = _calendar_map(read_csv(calendar_path))
    required = {"forecast_origin_id", "forecast_date", "forecast_cutoff_utc", "p0_date", "p0", "target_date", "actual_price", "return_y", "label_available_proxy_utc", "strict_pit_status"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("not a corrected historical X-Y candidate schema; legacy release rejected")
    ids = [r["forecast_origin_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate forecast_origin_id")
    output = []
    hard_blockers = ("P0_MISSING", "TARGET_PRICE_MISSING", "INVALID_", "NONPOSITIVE_", "INCOMPLETE_CONSECUTIVE_PRICE_WINDOW", "ISOLATED_KNOWN_2019_PRICE_CONFLICT", "MISSING_")
    def reject(row: dict[str, str], reason: str) -> None:
        if rejection_rows is not None:
            rejection_rows.append({"forecast_origin_id": row.get("forecast_origin_id", ""),
                                   "forecast_date": row.get("forecast_date", ""),
                                   "status": "BLOCKED", "reason": reason})
    for row in rows:
        if not row.get("return_y") or not row.get("p0") or not row.get("actual_price"):
            reject(row, "MISSING_P0_OR_LABEL")
            continue
        source_reasons = list(filter(None, row.get("reasons", "").split("|")))
        blocked_source = next((reason for reason in source_reasons if reason.startswith(hard_blockers)), None)
        if blocked_source:
            reject(row, "SOURCE_BLOCKER:" + blocked_source)
            continue
        try:
            target_rule_status = validate_candidate_row(row, lineage, cutoff, reference_prices, candidate_calendar)
        except (ValueError, KeyError) as exc:
            reject(row, "VALIDATION:" + str(exc))
            continue
        if row["forecast_date"] >= cutoff.date().isoformat():
            reject(row, "ORIGIN_NOT_BEFORE_FIT_CUTOFF")
            continue
        # Preserve the same seven-feature complete training pool for both candidates.
        try:
            all_features = {name: finite(row[name], name) for name in TRAINING_FEATURES}
        except (ValueError, KeyError) as exc:
            reject(row, "FEATURE_INVALID:" + str(exc))
            continue
        price_window = _price_window(lineage, row)
        price_hashes = sorted({x.get("source_file_sha256", "") for x in price_window})
        if any(len(value) != 64 for value in price_hashes):
            reject(row, "PRICE_SOURCE_HASH_MISSING")
            continue
        feature_lineage = {
            "RET5": {"observation_date": row["p0_date"], "window_first": price_window[-6]["observation_date"],
                     "window_last": row["p0_date"], "proxy_available_at_utc": row["p0_available_proxy_utc"],
                     "source_files_sha256": price_hashes},
            "RET20": {"observation_date": row["p0_date"], "window_first": row["price_window_start"],
                      "window_last": row["p0_date"], "proxy_available_at_utc": row["p0_available_proxy_utc"],
                      "source_files_sha256": price_hashes},
            "RV20": {"observation_date": row["p0_date"], "window_first": row["price_window_start"],
                     "window_last": row["p0_date"], "proxy_available_at_utc": row["p0_available_proxy_utc"],
                     "source_files_sha256": price_hashes},
        }
        for name in ("VIX", "UST10Y", "UST3M", "SPREAD"):
            feature_lineage[name] = {"observation_date": row[name + "_date"],
                                     "proxy_available_at_utc": row[name + "_available_proxy_utc"],
                                     "source_file": row.get(name + "_source_file", ""),
                                     "source_file_sha256": row.get(name + "_source_sha256", "")}
        if model_id == "VIX_UST10Y_RIDGE":
            feature_lineage = {name: feature_lineage[name] for name in MODELS[model_id]}
        feature_availability = [parse_utc(row[name + "_available_proxy_utc"], name) for name in ("VIX", "UST10Y", "UST3M", "SPREAD")]
        if max(feature_availability) > parse_utc(row["forecast_cutoff_utc"], "origin cutoff"):
            continue
        if verify_proxy_row("SPX_PRICE", row["p0_date"], row["p0_available_proxy_utc"], row["forecast_cutoff_utc"]) > parse_utc(row["forecast_cutoff_utc"], "origin cutoff"):
            continue
        label_available = proxy_available_at("SPX_PRICE", row["target_date"])
        if label_available != parse_utc(row["label_available_proxy_utc"], "label proxy") or label_available > cutoff:
            continue
        output.append({
            "forecast_origin_id": row["forecast_origin_id"], "forecast_date": row["forecast_date"],
            "forecast_cutoff_utc": row["forecast_cutoff_utc"], "fit_cutoff_utc": cutoff.isoformat(),
            "p0_date": row["p0_date"], "p0": row["p0"], "target_date": row["target_date"],
            "actual_price_candidate": row["actual_price"], "forward_simple_return_candidate": row["return_y"],
            "label_available_at_proxy_utc": label_available.isoformat(),
            "training_eligibility": "PROXY_HISTORICAL_INPUTS", "strict_pit_status": "STRICT_PIT_UNKNOWN",
            "calendar_status": "ACTUAL_SESSION_COMPLETENESS_UNKNOWN", "target_rule_status": target_rule_status,
            "feature_values_json": json.dumps(all_features, sort_keys=True),
            "feature_lineage_json": json.dumps(feature_lineage, sort_keys=True),
            "source_price": row.get("p0_source", ""), "source_price_window_start": row.get("price_window_start", ""),
            "source_price_window_end": row.get("price_window_end", ""), "reasons": row.get("reasons", "")
        })
    output.sort(key=lambda x: (x["forecast_date"], x["forecast_origin_id"]))
    return output


def latest_expected_matured_weekly_origin(forecast_origin_utc: str) -> str:
    """For the fixed Nov-13 task, find the latest prior Friday whose Friday label matured."""
    origin = parse_utc(forecast_origin_utc, "forecast origin").astimezone(LONDON).date()
    cutoff = parse_utc(forecast_origin_utc, "forecast origin")
    candidate = origin - timedelta(days=7)
    while candidate.year >= 2010:
        target = candidate + timedelta(days=7)
        mature = proxy_available_at("SPX_PRICE", target.isoformat())
        if mature <= cutoff:
            return candidate.isoformat()
        candidate -= timedelta(days=7)
    raise ValueError("no historical weekly label matures before cutoff")


def validate_latest_matured_origin(training_rows: list[dict[str, str]], forecast_origin_utc: str) -> str:
    """Fail closed if an expanding training snapshot omits the latest eligible weekly origin."""
    if not training_rows:
        raise ValueError("no matured corrected-proxy training rows")
    expected = latest_expected_matured_weekly_origin(forecast_origin_utc)
    actual = max(row.get("forecast_date", "") for row in training_rows)
    if actual < expected:
        raise ValueError(f"corrected training history is incomplete: missing expected matured weekly origin {expected}")
    return expected


def write_training_candidates(output_path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("no proxy-eligible historical training candidates")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite {output_path}")
    with output_path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_live_input(row: dict[str, str], cutoff_utc: str, evidence_root: Path) -> None:
    """Require explicit source-time evidence; retrieval after cutoff alone is never enough."""
    required = ("source", "feature_code", "observation_date", "release_timestamp_utc", "available_at_utc",
                "retrieval_timestamp_utc", "source_version", "source_file_sha256",
                "evidence_type", "evidence_review_ref", "evidence_review_record_path", "evidence_review_record_sha256",
                "evidence_path", "evidence_sha256", "value",
                "source_file_path", "raw_date_field", "raw_value_field",
                "session_calendar_path", "session_calendar_sha256", "calendar_id")
    if any(not row.get(k) for k in required):
        raise ValueError("live row lacks required source/time/version evidence")
    if row["evidence_type"] not in {"OFFICIAL_RELEASE_TIMESTAMP", "PRE_CUTOFF_ARCHIVE_CAPTURE"}:
        raise ValueError("live row lacks an acceptable source-time evidence type")
    cutoff = parse_utc(cutoff_utc, "live cutoff")
    yahoo_capture = row.get("source_provider") == "YAHOO_FINANCE" and row["evidence_type"] == "PRE_CUTOFF_ARCHIVE_CAPTURE"
    official_capture = (row.get("source") in {"CBOE_VIX", "US_TREASURY_CURVE"} and
                        row["evidence_type"] == "PRE_CUTOFF_ARCHIVE_CAPTURE" and
                        row["release_timestamp_utc"] == "UNKNOWN")
    release = None if (yahoo_capture or official_capture) and row["release_timestamp_utc"] == "UNKNOWN" else parse_utc(row["release_timestamp_utc"], "release time")
    available = parse_utc(row["available_at_utc"], "available time")
    retrieval = parse_utc(row["retrieval_timestamp_utc"], "retrieval time")
    if ((release is not None and (release > available or release > cutoff)) or
        available > cutoff or retrieval < available):
        raise ValueError("live input was not evidenced as available by cutoff")
    if len(row["source_file_sha256"]) != 64 or len(row["evidence_sha256"]) != 64:
        raise ValueError("live raw/evidence SHA-256 missing")
    source_file = (evidence_root / row["source_file_path"]).resolve()
    if not source_file.is_file() or sha256(source_file) != row["source_file_sha256"]:
        raise ValueError("live raw source file missing or hash mismatch")
    _verify_raw_record(row, evidence_root)
    if row.get("source_provider") == "YAHOO_FINANCE":
        _verify_yahoo_capture_and_source_approval(row, evidence_root, cutoff)
    if official_capture:
        _verify_official_pre_cutoff_capture(row, evidence_root, cutoff)
    evidence = (evidence_root / row["evidence_path"]).resolve()
    if not evidence.is_file() or sha256(evidence) != row["evidence_sha256"]:
        raise ValueError("live availability evidence missing or hash mismatch")
    if retrieval > cutoff and row["evidence_type"] != "OFFICIAL_RELEASE_TIMESTAMP":
        raise ValueError("post-cutoff retrieval requires an official timestamp proving earlier availability")
    if not row["evidence_review_ref"].strip():
        raise ValueError("live evidence requires a human review reference")
    review_path = (evidence_root / row["evidence_review_record_path"]).resolve()
    if not review_path.is_file() or sha256(review_path) != row["evidence_review_record_sha256"]:
        raise ValueError("human source-evidence review record missing or hash mismatch")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    for field, expected in (("decision", "CONFIRMED_PRE_CUTOFF"), ("source", row["source"]),
                            ("observation_date", row["observation_date"]),
                            ("release_timestamp_utc", row["release_timestamp_utc"]),
                            ("available_at_utc", row["available_at_utc"]),
                            ("evidence_sha256", row["evidence_sha256"]),
                            ("source_file_sha256", row["source_file_sha256"]),
                            ("session_calendar_sha256", row["session_calendar_sha256"]),
                            ("source_version", row["source_version"]),
                            ("feature_code", row["feature_code"]),
                            ("value", row["value"]),
                            ("retrieval_timestamp_utc", row["retrieval_timestamp_utc"]),
                            ("raw_date_field", row["raw_date_field"]),
                            ("raw_value_field", row["raw_value_field"]),
                            ("raw_version_field", row.get("raw_version_field", "")),
                            ("calendar_id", row["calendar_id"]),
                            ("index_type", row.get("index_type", "")),
                            ("session_close_utc", row.get("session_close_utc", "")),
                            ("conflict_status", row.get("conflict_status", ""))):
        if review.get(field) != expected:
            raise ValueError(f"human review record does not bind {field}")
    if not review.get("reviewer") or not review.get("review_reference"):
        raise ValueError("human review record lacks reviewer/reference")
    if row.get("source_provider") == "YAHOO_FINANCE":
        for field in ("source_provider", "source_capture_path", "source_capture_sha256", "source_url",
                      "source_provider_approval_record_path", "source_provider_approval_record_sha256"):
            if review.get(field) != row.get(field):
                raise ValueError(f"Yahoo human review record does not bind {field}")
    if official_capture:
        for field in ("source_capture_path", "source_capture_sha256", "source_url"):
            if review.get(field) != row.get(field):
                raise ValueError(f"official human review record does not bind {field}")
    observation = date.fromisoformat(row["observation_date"])
    if observation > cutoff.date():
        raise ValueError("live input observation date is after cutoff")
    calendar_path = (evidence_root / row["session_calendar_path"]).resolve()
    if not calendar_path.is_file() or sha256(calendar_path) != row["session_calendar_sha256"]:
        raise ValueError("source-specific session calendar missing or hash mismatch")
    calendar_rows = read_csv(calendar_path)
    calendar_keys = [(r.get("calendar_id"), r.get("session_date")) for r in calendar_rows]
    if len(calendar_keys) != len(set(calendar_keys)):
        raise ValueError("duplicate source calendar sessions")
    matches = [x for x in calendar_rows if x.get("calendar_id") == row["calendar_id"] and x.get("session_date") == observation.isoformat()]
    if len(matches) != 1:
        raise ValueError("observation date lacks a unique verified source-specific session")
    session_close = _session_completed_by(matches[0], row["calendar_id"], cutoff)
    if session_close is None:
        raise ValueError("observation date lacks a verified source-specific completion bound")
    if matches[0].get("session_status") == "VERIFIED_AVAILABLE_BY":
        if (row["source"] != "US_TREASURY_CURVE" or not official_capture
                or row.get("session_close_utc", "") not in ("", "UNKNOWN")
                or row.get("verified_available_by_utc") != matches[0].get("verified_available_by_utc")
                or available != session_close or retrieval != session_close
                or review.get("verified_available_by_utc") != row.get("verified_available_by_utc")
                or matches[0].get("source_file_sha256") != row["source_file_sha256"]
                or matches[0].get("source_capture_sha256") != row.get("source_capture_sha256")):
            raise ValueError("Treasury available-by bound is not source/capture/human-review bound")
    if (release or available) < session_close:
        raise ValueError("source release time precedes the observation session close")
    if row["source"] == "SPX_PRICE":
        if row.get("index_type") != "SP500_PRICE_INDEX":
            raise ValueError("live price is not the S&P 500 Price Index")
        session_evidence = (evidence_root / matches[0].get("session_evidence_path", "")).resolve()
        session_evidence_sha = matches[0].get("session_evidence_sha256", "")
        session_evidence_url = matches[0].get("session_evidence_url", "")
        if (len(session_evidence_sha) != 64 or not session_evidence.is_file()
                or sha256(session_evidence) != session_evidence_sha
                or not session_evidence_url.startswith("https://tv.nyse.com/2026-nyse-closing-bell/")
                or session_evidence_url not in session_evidence.read_text(encoding="utf-8")):
            raise ValueError("SPX session lacks bound NYSE actual-session evidence")
        close = parse_utc(row.get("session_close_utc", ""), "SPX session close")
        calendar_close = session_close
        if close != calendar_close or close > cutoff:
            raise ValueError("SPX session close does not match the verified calendar or is after cutoff")
    else:
        expected_calendar = "CBOE_VIX" if row["source"] == "CBOE_VIX" else "TREASURY"
        if row["calendar_id"] != expected_calendar:
            raise ValueError("nonprice input uses the wrong source-specific calendar")
    finite(row["value"], row["feature_code"])
    # Retrieval timestamp is recorded; it is not used to assert earlier availability.


def verify_human_approval(path: Path, *, model_id: str, cutoff_utc: str,
                          rules_sha256: str, training_manifest_sha256: str,
                          live_bundle_sha256: str) -> dict:
    approval = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "scope": "LIVE_PROXY_FINAL_FORECAST",
        "model_id": model_id,
        "forecast_cutoff_utc": cutoff_utc,
        "rules_sha256": rules_sha256,
        "training_manifest_sha256": training_manifest_sha256,
        "live_bundle_sha256": live_bundle_sha256,
    }
    for key, value in expected.items():
        if approval.get(key) != value:
            raise ValueError(f"human approval record mismatch: {key}")
    if not approval.get("decision_reference"):
        raise ValueError("human approval record lacks decision reference")
    if approval.get("strict_pit_status") == "VERIFIED":
        raise ValueError("approval record cannot promote Strict PIT; historical training remains proxy-based")
    # A stand-alone JSON string is not proof that a human approved this run.
    # Require the exact approval record to be present in the append-only project
    # log and bind it by the SHA-256 of its original JSONL line.
    expected_log_hash = approval.get("approval_log_record_sha256", "")
    if len(expected_log_hash) != 64:
        raise ValueError("approval must reference a matching governance approval-log record")
    log_path = ROOT / "governance/approval_log.jsonl"
    if not log_path.is_file():
        raise ValueError("governance approval log missing")
    matched = False
    for line in log_path.read_bytes().splitlines():
        if hashlib.sha256(line).hexdigest() != expected_log_hash:
            continue
        record = json.loads(line)
        log_expected = {**expected, "decision": "approved", "decision_reference": approval["decision_reference"]}
        if any(record.get(key) != value for key, value in log_expected.items()):
            raise ValueError("approval-log entry does not bind this exact model/cutoff/configuration")
        if record.get("strict_pit_status") == "VERIFIED":
            raise ValueError("approval-log entry cannot promote Strict PIT")
        matched = True
        break
    if not matched:
        raise ValueError("matching approval record not found in governance approval log")
    return approval


def build_live_feature_row(*, model_id: str, price_records: list[dict[str, str]],
                           vix_records: list[dict[str, str]], treasury_records: list[dict[str, str]],
                           cutoff_utc: str, target_session: str, evidence_root: Path) -> dict:
    """Validate source records and construct current features without proxy timestamps."""
    if model_id not in MODELS:
        raise ValueError("unregistered model id")
    cutoff = parse_utc(cutoff_utc, "live cutoff")
    local = cutoff.astimezone(LONDON)
    if local.weekday() != 4 or (local.hour, local.minute, local.second) != (12, 0, 0):
        raise ValueError("live cutoff must be Friday 12:00 Europe/London")
    required_price_count = 21 if model_id == "SEVEN_FACTOR_RIDGE" else 1
    if len(price_records) != required_price_count:
        raise ValueError(f"live price snapshot must contain exactly {required_price_count} verified SPX row(s)")
    prices = sorted(price_records, key=lambda r: r["observation_date"])
    for row in prices:
        if row.get("source") != "SPX_PRICE":
            raise ValueError("rolling window contains non-SPX source")
        verify_live_input(row, cutoff_utc, evidence_root)
        if row.get("conflict_status", "") not in ("", "NONE"):
            raise ValueError("known price conflict in rolling window")
    dates = [r["observation_date"] for r in prices]
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate price observations")
    if any(r.get("source_provider") == "YAHOO_FINANCE" for r in prices):
        if any(r.get("source_provider") != "YAHOO_FINANCE" for r in prices):
            raise ValueError("Yahoo price window cannot silently mix price providers")
        if len({(r["source_file_sha256"], r["source_version"]) for r in prices}) != 1:
            raise ValueError("Yahoo price window must use one frozen raw response/version")
    calendar_path = (evidence_root / prices[-1]["session_calendar_path"]).resolve()
    calendar_rows = read_csv(calendar_path)
    local_origin = cutoff.astimezone(LONDON)
    nominal_target = local_origin.date() + timedelta(days=7)
    target = date.fromisoformat(target_session)
    if target == nominal_target:
        target_rows = [r for r in calendar_rows if r.get("calendar_id") == "SPX" and r.get("session_date") == target_session]
        if len(target_rows) != 1:
            raise ValueError("next-Friday target calendar record is not unique")
        target_row = target_rows[0]
        if target_row.get("session_status") == "PLANNED_OPEN":
            if target_session != "2026-11-20" or target_row.get("actual_session_status") != "UNKNOWN":
                raise ValueError("planned target exemption is restricted to 2026-11-20 with actual session UNKNOWN")
            plan_path_text = target_row.get("plan_evidence_path", "")
            plan_sha = target_row.get("plan_evidence_sha256", "")
            review_text = target_row.get("plan_review_record_path", "")
            review_sha = target_row.get("plan_review_record_sha256", "")
            if not all((plan_path_text, plan_sha, review_text, review_sha)):
                raise ValueError("future planned target lacks official plan and review evidence")
            plan_path = (evidence_root / plan_path_text).resolve()
            review_path = (evidence_root / review_text).resolve()
            if (not plan_path.is_file() or sha256(plan_path) != plan_sha or
                not review_path.is_file() or sha256(review_path) != review_sha):
                raise ValueError("future planned target evidence/review hash mismatch")
            plan_review = json.loads(review_path.read_text(encoding="utf-8"))
            if (plan_review.get("decision") != "CONFIRMED_PLANNED_OPEN" or
                plan_review.get("target_session") != target_session or
                plan_review.get("plan_evidence_sha256") != plan_sha or
                not plan_review.get("reviewer") or not plan_review.get("review_reference")):
                raise ValueError("future target lacks matching human plan review")
        elif target_row.get("session_status") != "VERIFIED":
            raise ValueError("next-Friday target is neither verified nor approved planned-open")
        if parse_utc(target_row.get("session_close_utc", ""), "target close") <= cutoff:
            raise ValueError("target session close is not after forecast cutoff")
    else:
        if not (local_origin.date() + timedelta(days=3) <= target < nominal_target):
            raise ValueError("target must be next Friday or a prior session in the target week")
        nominal_rows = [r for r in calendar_rows if r.get("calendar_id") == "SPX" and r.get("session_date") == nominal_target.isoformat()]
        if len(nominal_rows) != 1 or nominal_rows[0].get("session_status") != "VERIFIED_CLOSED":
            raise ValueError("cannot apply target fallback without verified Friday closure evidence")
        candidates = [date.fromisoformat(r["session_date"]) for r in calendar_rows
                      if r.get("calendar_id") == "SPX" and r.get("session_status") == "VERIFIED"
                      and local_origin.date() + timedelta(days=3) <= date.fromisoformat(r["session_date"]) < nominal_target]
        if not candidates or max(candidates) != target:
            raise ValueError("target is not the latest verified prior session in the target week")
        target_row = next(r for r in calendar_rows if r.get("calendar_id") == "SPX" and r.get("session_date") == target_session)
        if parse_utc(target_row.get("session_close_utc", ""), "fallback target close") <= cutoff:
            raise ValueError("fallback target close is not after forecast cutoff")
    sessions = sorted(r["session_date"] for r in calendar_rows
                      if r.get("calendar_id") == "SPX" and r.get("session_status") == "VERIFIED"
                      and parse_utc(r.get("session_close_utc", ""), "calendar close") <= cutoff)
    if not sessions or dates[-1] != sessions[-1]:
        raise ValueError("P0 is not the latest verified completed SPX session before cutoff")
    if model_id == "SEVEN_FACTOR_RIDGE" and (len(sessions) < 21 or dates != sessions[-21:]):
        raise ValueError("price rows do not equal the last 21 verified SPX sessions before cutoff")
    values = [finite(r["value"], "SPX price") for r in prices]
    if any(v <= 0 for v in values):
        raise ValueError("nonpositive SPX price")
    p0 = values[-1]
    feature_values = {}
    if model_id == "SEVEN_FACTOR_RIDGE":
        daily_returns = [values[i] / values[i - 1] - 1 for i in range(1, 21)]
        mean = sum(daily_returns) / 20
        feature_values.update({
            "RET5": values[-1] / values[-6] - 1,
            "RET20": values[-1] / values[0] - 1,
            "RV20": math.sqrt(sum((x - mean) ** 2 for x in daily_returns) / 19),
        })
    if not vix_records:
        if "VIX" in MODELS[model_id]:
            raise ValueError("live VIX value missing")
    verified_vix = []
    for row in vix_records:
        if row.get("source") != "CBOE_VIX" or row.get("feature_code") != "VIX":
            raise ValueError("VIX input source/field mismatch")
        verify_live_input(row, cutoff_utc, evidence_root)
        verified_vix.append(row)
    if verified_vix:
        if len({r["observation_date"] for r in verified_vix}) != len(verified_vix):
            raise ValueError("multiple VIX rows on one observation date; version choice is unresolved")
        latest_vix = max(verified_vix, key=lambda r: r["observation_date"])
        cal = read_csv((evidence_root / latest_vix["session_calendar_path"]).resolve())
        latest_vix_session = _latest_verified_session(cal, "CBOE_VIX", cutoff)
        if latest_vix["observation_date"] != latest_vix_session:
            raise ValueError("VIX observation is not the latest verified completed Cboe session")
        sessions_vix = [x for x in cal if x.get("calendar_id") == "CBOE_VIX" and x.get("session_status") == "VERIFIED"
                        and parse_utc(x.get("session_close_utc", ""), "VIX calendar close") <= cutoff]
        age = sum(x["session_date"] > latest_vix["observation_date"] for x in sessions_vix)
        if age > 5:
            raise ValueError("VIX exceeds five verified source sessions of staleness")
        feature_values["VIX"] = finite(latest_vix["value"], "VIX")
    verified_treasury = {}
    for row in treasury_records:
        code = row.get("feature_code", "")
        if code not in {"UST10Y", "UST3M", "UST2Y"} or row.get("source") != "US_TREASURY_CURVE":
            raise ValueError("Treasury source/tenor mismatch")
        verify_live_input(row, cutoff_utc, evidence_root)
        if code in verified_treasury:
            raise ValueError("multiple Treasury versions for a tenor; freeze version choice first")
        verified_treasury[code] = row
    needed_tenors = {"UST10Y", "UST3M", "UST2Y"} if model_id == "SEVEN_FACTOR_RIDGE" else {"UST10Y"}
    if not needed_tenors.issubset(verified_treasury):
        raise ValueError("required Treasury tenors missing")
    if model_id == "SEVEN_FACTOR_RIDGE":
        tenor_dates = {verified_treasury[x]["observation_date"] for x in ("UST10Y", "UST3M", "UST2Y")}
        if len(tenor_dates) != 1:
            raise ValueError("Treasury factor group must come from one curve observation/version")
        for code in ("UST10Y", "UST3M", "UST2Y"):
            feature_values[code] = finite(verified_treasury[code]["value"], code)
        feature_values["SPREAD"] = feature_values["UST10Y"] - feature_values["UST2Y"]
    else:
        feature_values["UST10Y"] = finite(verified_treasury["UST10Y"]["value"], "UST10Y")
    for row in verified_treasury.values():
        cal = read_csv((evidence_root / row["session_calendar_path"]).resolve())
        latest_treasury_session = _latest_verified_session(cal, "TREASURY", cutoff)
        if row["observation_date"] != latest_treasury_session:
            raise ValueError(f"{row['feature_code']} is not from the latest verified completed Treasury session")
        sessions_tsy = [x for x in cal if x.get("calendar_id") == "TREASURY"
                        and (bound := _session_completed_by(x, "TREASURY", cutoff)) is not None
                        and bound <= cutoff]
        age = sum(x["session_date"] > row["observation_date"] for x in sessions_tsy)
        if age > 5:
            raise ValueError("Treasury input exceeds five verified source sessions of staleness")
    if any(not math.isfinite(feature_values[f]) for f in MODELS[model_id]):
        raise ValueError("non-finite or missing live feature")
    # Historical source calendars and vintages remain unknown even when current
    # source timestamp evidence passes.
    return {"forecast_cutoff_utc": cutoff.isoformat(), "target_session": target_session, "P0": p0,
            "P0_observation_date": prices[-1]["observation_date"],
            "features": {k: feature_values[k] for k in MODELS[model_id]},
            "live_input_status": "LIVE_INPUTS_CUTOFF_VERIFIED",
            "historical_training_status": "PROXY_HISTORICAL_INPUTS",
            "strict_pit_status": "STRICT_PIT_UNKNOWN"}


def _fit_ridge_pipeline(*, model_id: str, train_rows: list[dict[str, float]],
                        feature_row: dict[str, float], p0: float) -> dict:
    if model_id not in MODELS or len(train_rows) < 10 or p0 <= 0:
        raise ValueError("model, training count, or P0 gate failed")
    features = MODELS[model_id]
    X = [[finite(str(row[f]), f) for f in features] for row in train_rows]
    y = [finite(str(row["Y"]), "Y") for row in train_rows]
    xv = [[finite(str(feature_row[f]), f) for f in features]]
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    pipeline = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    pipeline.fit(X, y)
    predicted_return = float(pipeline.predict(xv)[0])
    predicted_price = p0 * (1 + predicted_return)
    if not math.isfinite(predicted_price):
        raise ValueError("non-finite prediction")
    return {"predicted_return": predicted_return, "predicted_price": predicted_price,
            "model_status": "PROVISIONAL", "strict_pit_status": "STRICT_PIT_UNKNOWN",
            "run_type": "UNSET_INTERNAL"}


def fit_predict_synthetic(*, model_id: str, train_rows: list[dict[str, float]],
                          feature_row: dict[str, float], p0: float) -> dict:
    """Synthetic-only fit path used to exercise scaling and price conversion."""
    result = _fit_ridge_pipeline(model_id=model_id, train_rows=train_rows, feature_row=feature_row, p0=p0)
    result["run_type"] = "SYNTHETIC_TEST_ONLY"
    return result


def run_approved_live_candidate(*, model_id: str, training_csv: Path, training_manifest: Path,
                                approval_path: Path, live_snapshot: dict, live_snapshot_path: Path,
                                evidence_root: Path,
                                rules_path: Path, protocol_path: Path, output_path: Path) -> dict:
    """Future-only live candidate path. No call is made during this repair task."""
    if output_path.exists():
        raise FileExistsError("refusing to overwrite forecast output")
    if not live_snapshot_path.is_file():
        raise ValueError("frozen Live bundle file missing")
    live_bundle_sha = sha256(live_snapshot_path)
    if json.loads(live_snapshot_path.read_text(encoding="utf-8")) != live_snapshot:
        raise ValueError("Live input object differs from frozen bundle file")
    rules = verify_corrected_rules(rules_path, protocol_path)
    frozen = verify_frozen_manifest(training_manifest)
    if frozen.get("run_type") != "HISTORICAL_CORRECTED_PROXY_CANDIDATE_ONLY" or frozen.get("model_id") != model_id:
        raise ValueError("training manifest is not a matching corrected-proxy snapshot")
    cutoff_text = live_snapshot.get("cutoff_utc", "")
    cutoff = parse_utc(cutoff_text, "live cutoff")
    if cutoff != parse_utc(frozen.get("forecast_cutoff_utc", ""), "training manifest cutoff"):
        raise ValueError("training candidate was not frozen for this fit cutoff")
    if sha256(training_csv) != frozen["files_sha256"].get(str(training_csv.resolve())):
        raise ValueError("training candidate CSV is not bound to the frozen manifest")
    model_candidates_path = Path(__file__).resolve().parent / "model_candidates.json"
    if (not model_candidates_path.is_file() or
        frozen["files_sha256"].get(str(model_candidates_path.resolve())) != sha256(model_candidates_path)):
        raise ValueError("approved model candidates file is not bound before model fit")
    approval = verify_human_approval(approval_path, model_id=model_id, cutoff_utc=cutoff.isoformat(),
        rules_sha256=sha256(rules_path), training_manifest_sha256=sha256(training_manifest),
        live_bundle_sha256=live_bundle_sha)
    origin = parse_utc(live_snapshot.get("forecast_origin_timestamp", ""), "forecast origin")
    if origin != cutoff or origin.astimezone(LONDON).weekday() != 4 or (origin.astimezone(LONDON).hour, origin.astimezone(LONDON).minute) != (12, 0):
        raise ValueError("live cutoff/origin must be the same Friday 12:00 Europe/London instant")
    if live_snapshot.get("target_session") != (origin.astimezone(LONDON).date() + timedelta(days=7)).isoformat():
        raise ValueError("live target must be the following Friday; fallback requires separately reviewed session mapping")
    if origin.isoformat() != "2026-11-13T12:00:00+00:00" or live_snapshot.get("target_session") != "2026-11-20":
        raise ValueError("this release is restricted to the 2026-11-13 cutoff and 2026-11-20 target")
    live = build_live_feature_row(model_id=model_id, price_records=live_snapshot.get("price_records", []),
        vix_records=live_snapshot.get("vix_records", []), treasury_records=live_snapshot.get("treasury_records", []),
        cutoff_utc=cutoff.isoformat(), target_session=live_snapshot["target_session"], evidence_root=evidence_root)
    if live["strict_pit_status"] != "STRICT_PIT_UNKNOWN":
        raise ValueError("strict PIT cannot be promoted by live input checks")
    train_rows = read_csv(training_csv)
    selected = []
    for row in train_rows:
        if row.get("training_eligibility") != "PROXY_HISTORICAL_INPUTS" or row.get("strict_pit_status") != "STRICT_PIT_UNKNOWN":
            continue
        if row.get("forecast_date", "") >= origin.astimezone(LONDON).date().isoformat():
            continue
        maturity = parse_utc(row.get("label_available_at_proxy_utc", ""), "training label proxy")
        if maturity > cutoff:
            continue
        features = json.loads(row["feature_values_json"])
        selected.append({**{name: finite(str(features[name]), name) for name in TRAINING_FEATURES},
                         "Y": finite(row["forward_simple_return_candidate"], "training Y"),
                         **{name: row[name] for name in (
                             "forecast_origin_id", "forecast_date", "label_available_at_proxy_utc",
                             "training_eligibility", "strict_pit_status",
                             "forward_simple_return_candidate", "feature_values_json")}})
    if len(selected) < 10:
        raise ValueError("insufficient matured corrected-proxy training rows")
    expected_latest = validate_latest_matured_origin(selected, origin.isoformat())
    if sha256(live_snapshot_path) != live_bundle_sha:
        raise ValueError("frozen Live bundle changed before model fit")
    for suffix in ("_training_membership.csv", "_live_input_snapshot.json", "_execution_manifest.json"):
        if output_path.with_name(output_path.stem + suffix).exists():
            raise FileExistsError("refusing to overwrite partial forecast artifacts")
    consumed_path = approval_path.with_name(approval_path.stem + ".consumed.json")
    with consumed_path.open("x", encoding="utf-8") as consumed:
        json.dump({"status": "SINGLE_RUN_ATTEMPT_STARTED", "started_at_utc": datetime.now(timezone.utc).isoformat(),
                   "approval_sha256": sha256(approval_path), "training_manifest_sha256": sha256(training_manifest),
                   "live_bundle_sha256": live_bundle_sha, "output_path": str(output_path.resolve())}, consumed,
                  indent=2, sort_keys=True)
        consumed.write("\n")
    # Fit before writing any live-run artifacts so a dependency or numeric
    # failure cannot leave a manifest that looks like an executed forecast.
    model_rows = [{**{name: r[name] for name in TRAINING_FEATURES}, "Y": r["Y"]} for r in selected]
    result = _fit_ridge_pipeline(model_id=model_id, train_rows=model_rows,
                                 feature_row=live["features"], p0=float(live["P0"]))
    membership_path = output_path.with_name(output_path.stem + "_training_membership.csv")
    membership = [{"forecast_origin_id": r["forecast_origin_id"], "forecast_date": r["forecast_date"],
                   "fit_cutoff_utc": cutoff.isoformat(), "label_available_at_proxy_utc": r["label_available_at_proxy_utc"],
                   "training_eligibility": r["training_eligibility"], "strict_pit_status": r["strict_pit_status"],
                   "forward_simple_return_candidate": r["forward_simple_return_candidate"],
                   "feature_values_json": r["feature_values_json"]} for r in selected]
    write_csv_new(membership_path, membership)
    live_snapshot_path = output_path.with_name(output_path.stem + "_live_input_snapshot.json")
    if live_snapshot_path.exists():
        raise FileExistsError("refusing to overwrite live input snapshot")
    live_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_payload = dict(live_snapshot)
    snapshot_payload["computed_feature_snapshot"] = live
    live_snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    frozen_files = {str(training_csv.resolve()): sha256(training_csv),
                    str(training_manifest.resolve()): sha256(training_manifest),
                    str(live_snapshot_path.resolve()): live_bundle_sha,
                    str(approval_path.resolve()): sha256(approval_path),
                    str(rules_path.resolve()): sha256(rules_path),
                    str(protocol_path.resolve()): sha256(protocol_path),
                    str(Path(__file__).resolve()): sha256(Path(__file__).resolve()),
                    str(membership_path.resolve()): sha256(membership_path),
                    str(live_snapshot_path.resolve()): sha256(live_snapshot_path),
                    str(model_candidates_path.resolve()): sha256(model_candidates_path)}
    live_rows = (live_snapshot.get("price_records", []) + live_snapshot.get("vix_records", [])
                 + live_snapshot.get("treasury_records", []))
    for row in live_rows:
        for key, hash_key in (("source_file_path", "source_file_sha256"),
                              ("evidence_path", "evidence_sha256"),
                              ("evidence_review_record_path", "evidence_review_record_sha256"),
                              ("session_calendar_path", "session_calendar_sha256")):
            path = (evidence_root / row[key]).resolve()
            if not path.is_file() or sha256(path) != row[hash_key]:
                raise ValueError(f"live execution freeze input mismatch: {key}")
            frozen_files[str(path)] = row[hash_key]
        if row.get("source_provider") == "YAHOO_FINANCE" or row.get("evidence_type") == "PRE_CUTOFF_ARCHIVE_CAPTURE":
            extra = [("source_capture_path", "source_capture_sha256")]
            if row.get("source_provider") == "YAHOO_FINANCE":
                extra.append(("source_provider_approval_record_path", "source_provider_approval_record_sha256"))
            for key, hash_key in extra:
                path = (evidence_root / row[key]).resolve()
                if not path.is_file() or sha256(path) != row[hash_key]:
                    raise ValueError(f"source capture freeze input mismatch: {key}")
                frozen_files[str(path)] = row[hash_key]
    target_calendar = read_csv((evidence_root / live_snapshot["price_records"][-1]["session_calendar_path"]).resolve())
    planned = [r for r in target_calendar if r.get("calendar_id") == "SPX" and
               r.get("session_date") == live_snapshot["target_session"] and
               r.get("session_status") == "PLANNED_OPEN"]
    if planned:
        for key, hash_key in (("plan_evidence_path", "plan_evidence_sha256"),
                              ("plan_review_record_path", "plan_review_record_sha256")):
            path = (evidence_root / planned[0][key]).resolve()
            if not path.is_file() or sha256(path) != planned[0][hash_key]:
                raise ValueError(f"planned target freeze evidence mismatch: {key}")
            frozen_files[str(path)] = planned[0][hash_key]
    execution_manifest = {
        "manifest_version": "2.0", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_origin_timestamp_utc": origin.isoformat(), "information_cutoff_timestamp_utc": cutoff.isoformat(),
        "fit_cutoff_timestamp_utc": cutoff.isoformat(), "target_session": live_snapshot["target_session"],
        "run_type": "LIVE_PROXY_FINAL_CANDIDATE", "approval_status": "MATCHED_TO_EXTERNAL_HUMAN_DECISION",
        "approval_record_path": str(approval_path.resolve()), "approval_record_sha256": sha256(approval_path),
        "model_status": "PROVISIONAL", "model_id": model_id, "model_config": {
            "features": MODELS[model_id], "alpha": 1.0,
            "pipeline": "StandardScaler fit on current eligible expanding training rows then Ridge"},
        "proxy_rules_sha256": sha256(rules_path), "training_manifest_sha256": sha256(training_manifest),
        "live_bundle_sha256": live_bundle_sha,
        "live_input_status": "LIVE_INPUTS_CUTOFF_VERIFIED", "historical_training_status": "PROXY_HISTORICAL_INPUTS",
        "strict_pit_status": "STRICT_PIT_UNKNOWN", "formal_scoring_status": "NOT_AUTHORIZED",
        "files_sha256": frozen_files}
    execution_manifest_path = output_path.with_name(output_path.stem + "_execution_manifest.json")
    if execution_manifest_path.exists():
        raise FileExistsError("refusing to overwrite execution manifest")
    execution_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    execution_manifest_path.write_text(json.dumps(execution_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    execution_manifest_sha = sha256(execution_manifest_path)
    result.update({"run_type": "LIVE_PROXY_FINAL_CANDIDATE", "live_input_status": live["live_input_status"],
        "historical_training_status": "PROXY_HISTORICAL_INPUTS", "strict_pit_status": "STRICT_PIT_UNKNOWN",
        "forecast_origin_timestamp_utc": origin.isoformat(), "information_cutoff_timestamp_utc": cutoff.isoformat(),
        "fit_cutoff_timestamp_utc": cutoff.isoformat(), "target_session": live["target_session"],
        "P0_observation_date": live["P0_observation_date"], "features": live["features"],
        "model_id": model_id, "alpha": 1.0, "training_count": len(selected),
        "training_origin_ids_sha256": hashlib.sha256("\n".join(r["forecast_origin_id"] for r in selected).encode()).hexdigest(),
        "training_manifest_sha256": sha256(training_manifest), "approval_file_sha256": sha256(approval_path),
        "live_bundle_sha256": live_bundle_sha,
        "execution_manifest_path": str(execution_manifest_path), "execution_manifest_sha256": execution_manifest_sha,
        "approval_decision_reference": approval["decision_reference"], "rules_sha256": sha256(rules_path),
        "target_actual_price": "NOT_INCLUDED", "formal_scoring_status": "NOT_AUTHORIZED"})
    if output_path.exists():
        raise FileExistsError("refusing to overwrite forecast output")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def freeze_manifest(path: Path, *, files: Iterable[Path], rules_path: Path,
                    model_id: str, cutoff_utc: str, run_type: str) -> dict:
    if model_id not in MODELS:
        raise ValueError("unregistered model id")
    if run_type not in {"HISTORICAL_CORRECTED_PROXY_CANDIDATE_ONLY", "SYNTHETIC_TEST_ONLY", "LIVE_PROXY_CANDIDATE_ONLY"}:
        raise ValueError("run type is not an allowed non-formal v2 snapshot status")
    file_items = {}
    for item in sorted(set(Path(x).resolve() for x in files) | {rules_path.resolve(), Path(__file__).resolve()}):
        if not item.is_file():
            raise ValueError(f"cannot freeze missing input: {item}")
        file_items[str(item)] = sha256(item)
    manifest = {
        "manifest_version": "2.0", "run_type": run_type, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_cutoff_utc": cutoff_utc, "model_id": model_id, "model_status": "PROVISIONAL",
        "model_config": {"features": MODELS[model_id], "alpha": 1.0, "pipeline": "StandardScaler fit on current eligible training rows then Ridge"},
        "proxy_rules_path": str(rules_path.resolve()), "proxy_rules_sha256": sha256(rules_path),
        "protocol_sha256": PROTOCOL_SHA, "strict_pit_status": "STRICT_PIT_UNKNOWN",
        "files_sha256": file_items, "approval_status": "UNAPPROVED"}
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_frozen_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("protocol_sha256") != PROTOCOL_SHA or manifest.get("strict_pit_status") != "STRICT_PIT_UNKNOWN":
        raise ValueError("manifest protocol/Strict PIT status invalid")
    if manifest.get("model_status") != "PROVISIONAL":
        raise ValueError("model status cannot be promoted by manifest")
    if not manifest.get("files_sha256"):
        raise ValueError("empty file freeze")
    for raw_path, expected in manifest["files_sha256"].items():
        path_obj = Path(raw_path)
        if not path_obj.is_file() or sha256(path_obj) != expected:
            raise ValueError(f"frozen input changed: {raw_path}")
    rules_path = Path(manifest.get("proxy_rules_path", ""))
    if not rules_path.is_file() or sha256(rules_path) != manifest.get("proxy_rules_sha256"):
        raise ValueError("corrected rules file is not bound to manifest")
    if manifest["files_sha256"].get(str(rules_path.resolve())) != manifest.get("proxy_rules_sha256"):
        raise ValueError("rules hash differs between manifest fields")
    model_id = manifest.get("model_id")
    config = manifest.get("model_config", {})
    if model_id not in MODELS or config.get("features") != MODELS[model_id] or config.get("alpha") != 1.0:
        raise ValueError("frozen model config does not match registered candidate")
    return manifest
