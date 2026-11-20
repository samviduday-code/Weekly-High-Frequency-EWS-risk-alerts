#!/usr/bin/env python3
"""Add complete NPCI Sunday weeks to the panel.

NPCI blocks downloads from this cloud host. Two sources are tried, and the
one with the later last day is used:

1. A file saved from a normal browser at data/New/external_hf/npci_daily.csv
   (or the path in NPCI_DAILY_CSV).
2. The public Measure of India copy, which this host can download. That copy
   currently ends on 8 Oct 2026.

Wide CSV columns follow that public file. A long CSV with date, product_type,
volume, and value is also accepted.

Only Sunday weeks whose Sunday is on or before the file's last day are added.
A partial week is left out. Week-on-week change is the percent change in the
sum of the daily prints.
"""

from __future__ import annotations

import csv
import json
import os
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PANEL_PATH = ROOT / "New" / "external_hf" / "panel.json"
LOCAL_CSV = ROOT / "New" / "external_hf" / "npci_daily.csv"
DEFAULT_URL = "https://measure.thisindianlife.today/data/npci-daily.csv"

# id_prefix -> (wide column name, long product_type, "volume" or "value")
SERIES = {
    "atm_nfs_volume": ("ATM network (NFS) transactions, number of transactions, daily", "NFS", "volume"),
    "aeps_cash_withdrawals": ("AePS cash withdrawals, number of transactions, daily", "AEPS Cash Withdrawal", "volume"),
    "fastag_volume": ("FASTag (NETC) toll and parking, number of transactions, daily", "NETC Fastag", "volume"),
    "nach_debit_value": ("NACH debit, value, daily", "NACH Debit", "value"),
    "imps_value": ("IMPS, value, daily", "IMPS", "value"),
    "upi_volume": ("UPI, number of transactions, daily", "UPI", "volume"),
    "upi_value_weekly": ("UPI, value, daily", "UPI", "value"),
    "imps_volume": ("IMPS, number of transactions, daily", "IMPS", "volume"),
    "nach_debit_volume": ("NACH debit, number of transactions, daily", "NACH Debit", "volume"),
}


def parse_day(value: str) -> date:
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {value!r}")


def sunday_on_or_after(day: date) -> date:
    return day + timedelta(days=(6 - day.weekday()) % 7)


def load_wide(path: Path) -> tuple[date, dict[date, dict[str, float]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = {name: spec[0] for name, spec in SERIES.items()}
        by_day: dict[date, dict[str, float]] = {}
        last_day: date | None = None
        for row in reader:
            if not row.get("date"):
                continue
            day = parse_day(row["date"])
            last_day = day if last_day is None or day > last_day else last_day
            by_day[day] = {}
            for series_id, column in columns.items():
                raw = (row.get(column) or "").strip()
                by_day[day][series_id] = float(raw) if raw else 0.0
    if last_day is None:
        raise ValueError(f"{path} has no dated rows")
    return last_day, by_day


def load_long(path: Path) -> tuple[date, dict[date, dict[str, float]]]:
    wanted = {(spec[1], spec[2]): series_id for series_id, spec in SERIES.items()}
    by_day: dict[date, dict[str, float]] = {}
    last_day: date | None = None
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row.get("date") or not row.get("product_type"):
                continue
            day = parse_day(row["date"])
            last_day = day if last_day is None or day > last_day else last_day
            by_day.setdefault(day, {})
            product = row["product_type"].strip()
            for field, series_id in (
                ("volume", wanted.get((product, "volume"))),
                ("value", wanted.get((product, "value"))),
            ):
                if series_id is None:
                    continue
                raw = (row.get(field) or "").strip()
                by_day[day][series_id] = float(raw) if raw else 0.0
    if last_day is None:
        raise ValueError(f"{path} has no dated rows")
    return last_day, by_day


def load_csv(path: Path) -> tuple[date, dict[date, dict[str, float]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        header = handle.readline()
    if "product_type" in header and "volume" in header:
        return load_long(path)
    return load_wide(path)


def download(url: str, dest: Path) -> bool:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ews-weekly"})
        with urllib.request.urlopen(request, timeout=40) as response:
            dest.write_bytes(response.read())
    except OSError as exc:
        print(f"npci download failed: {exc}")
        return False
    return dest.is_file() and dest.stat().st_size > 0


NPCI_SERIES = {
    "atm_nfs_volume": ("nfs", "nfs-daily-statistics", "nfs_volume_mn"),
    "aeps_cash_withdrawals": ("aeps", "aeps-cash-withdrawal", "aeps_cash_withdrawal_volume_mn"),
    "fastag_volume": ("netc", "netc-daily-statistics", "netc_volume_mn"),
    "nach_debit_value": ("nach", "nach-debit-daily-statistics", "nach_debit_value_crores"),
    "nach_debit_volume": ("nach", "nach-debit-daily-statistics", "nach_debit_volume_mn"),
    "imps_value": ("imps", "imps-daily-statistics", "imps_value_crores"),
    "imps_volume": ("imps", "imps-daily-statistics", "imps_volume_mn"),
    "upi_volume": ("upi", "upi-daily-statistics", "upi_volume_mn"),
    "upi_value_weekly": ("upi", "upi-daily-statistics", "upi_value_crores"),
}


def npci_get(product: str, tab: str, month: str) -> list[dict]:
    try:
        from curl_cffi import requests
    except ImportError:
        print("curl_cffi is not installed; skipping the NPCI JSON API")
        return []
    url = (
        "https://www.npci.org.in/api/product-statistic/tab/detail"
        f"?product_name={product}&tab_name={tab}&excel_type=daily"
        f"&year=2026&month={month}&page_no=1&page_size=100"
    )
    referer = f"https://www.npci.org.in/product/{product}/product-statistics"
    last_error = "no response"
    for attempt in range(4):
        try:
            response = requests.get(
                url,
                impersonate="chrome",
                timeout=40,
                headers={"Referer": referer},
            )
        except OSError as exc:
            last_error = str(exc)
            response = None
        if response is not None and response.status_code == 200:
            payload = response.json()
            rows = (payload.get("data") or {}).get("results") or []
            return [row for row in rows if str(row.get("npci_day", "")).lower() != "total"]
        status = response.status_code if response is not None else "error"
        last_error = f"HTTP {status}"
        time.sleep(3 * (attempt + 1))
    print(f"npci {product} {month} failed: {last_error}")
    return []


def load_npci_api() -> tuple[date | None, dict[date, dict[str, float]]]:
    by_day: dict[date, dict[str, float]] = {}
    last_day: date | None = None
    seen: set[tuple[str, str, str]] = set()
    for _series_id, (product, tab, field) in NPCI_SERIES.items():
        key = (product, tab, field)
        if key in seen:
            continue
        seen.add(key)
        for month in ("September", "October", "November"):
            rows = npci_get(product, tab, month)
            if rows and field not in rows[0]:
                print(f"npci {product} {tab} has no {field}; keys={sorted(rows[0])}")
            for row in rows:
                if field not in row or not row.get("npci_day"):
                    continue
                try:
                    day = datetime.strptime(str(row["npci_day"]), "%B %d, %Y").date()
                    value = float(str(row[field]).replace(",", ""))
                except (TypeError, ValueError):
                    continue
                by_day.setdefault(day, {})
                # field is unique per series; map back below
                by_day[day][field] = value
                last_day = day if last_day is None or day > last_day else last_day
            time.sleep(1.2)
    mapped: dict[date, dict[str, float]] = {}
    field_to_series = {field: series_id for series_id, (*_rest, field) in NPCI_SERIES.items()}
    for day, fields in by_day.items():
        mapped[day] = {}
        for field, value in fields.items():
            series_id = field_to_series.get(field)
            if series_id:
                mapped[day][series_id] = value
    return last_day, mapped


def choose_source() -> tuple[Path | None, str]:
    override = os.environ.get("NPCI_DAILY_CSV", "").strip()
    local = Path(override) if override else LOCAL_CSV
    url = os.environ.get("NPCI_DAILY_URL", DEFAULT_URL).strip()
    downloaded = ROOT / "New" / "external_hf" / ".npci_daily_download.csv"
    fetched = download(url, downloaded) if url else False
    candidates: list[tuple[date, Path, str]] = []
    if local.is_file():
        last_day, _ = load_csv(local)
        candidates.append((last_day, local, "local file"))
    if fetched:
        last_day, _ = load_csv(downloaded)
        candidates.append((last_day, downloaded, url))
    if not candidates:
        return None, "no NPCI daily file"
    candidates.sort(key=lambda item: item[0])
    last_day, path, label = candidates[-1]
    return path, f"{label} through {last_day.isoformat()}"


def complete_week_totals(by_day: dict[date, dict[str, float]], last_day: date) -> dict[date, dict[str, float]]:
    totals: dict[date, dict[str, float]] = {}
    for day, values in by_day.items():
        sunday = sunday_on_or_after(day)
        if sunday > last_day:
            continue
        bucket = totals.setdefault(sunday, {series_id: 0.0 for series_id in SERIES})
        for series_id in SERIES:
            bucket[series_id] += values.get(series_id, 0.0)
    return totals


def wow(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


def append_weeks(panel: dict, totals: dict[date, dict[str, float]]) -> int:
    by_id = {series["id_prefix"]: series for series in panel.get("series", [])}
    added = 0
    sundays = sorted(totals)
    for index, sunday in enumerate(sundays):
        if index == 0:
            continue
        previous = sundays[index - 1]
        if (sunday - previous).days != 7:
            continue
        for series_id in SERIES:
            series = by_id.get(series_id)
            if series is None or series.get("cadence") != "weekly":
                continue
            known = {obs["date"] for obs in series.get("observations", [])}
            stamp = sunday.isoformat()
            if stamp in known:
                continue
            series.setdefault("observations", []).append(
                {"date": stamp, "value": wow(totals[sunday][series_id], totals[previous][series_id])}
            )
            series["observations"].sort(key=lambda obs: obs["date"])
            added += 1
    return added


def main() -> int:
    by_day: dict[date, dict[str, float]] = {}
    last_day: date | None = None
    labels: list[str] = []
    if os.environ.get("NPCI_FETCH", "1") != "0":
        api_last, api_days = load_npci_api()
        if api_last is not None:
            by_day.update(api_days)
            last_day = api_last
            labels.append(f"NPCI JSON through {api_last.isoformat()}")
    path, label = choose_source()
    if path is not None:
        csv_last, csv_days = load_csv(path)
        for day, values in csv_days.items():
            slot = by_day.setdefault(day, {})
            for series_id, value in values.items():
                slot.setdefault(series_id, value)
        if last_day is None or csv_last > last_day:
            last_day = csv_last
        labels.append(label)
    if last_day is None:
        print(
            "NPCI daily file not available. Save a browser download at "
            f"{LOCAL_CSV} and run again. Weekly columns stay as they are."
        )
        return 0
    label = "; ".join(labels)
    totals = complete_week_totals(by_day, last_day)
    panel = json.loads(PANEL_PATH.read_text(encoding="utf-8"))
    added = append_weeks(panel, totals)
    if added:
        PANEL_PATH.write_text(json.dumps(panel, indent=2) + "\n", encoding="utf-8")
    last_sunday = max(totals) if totals else None
    print(
        f"npci source: {label}; last complete Sunday "
        f"{last_sunday.isoformat() if last_sunday else 'none'}; "
        f"new weekly observations={added}"
    )
    if last_sunday is not None and last_sunday < date(2026, 11, 15):
        print(
            "Later Sunday weeks are not in this file. Download a newer daily "
            f"CSV in a browser and save it as {LOCAL_CSV}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
