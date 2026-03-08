#!/usr/bin/env python3
"""
extract_cldr.py - Extract resolved CLDR locale data from the official Unicode CLDR repository.

Properly resolves CLDR inheritance (↑↑↑ markers and absent values) by walking the
locale parent chain (e.g., de_DE → de → root). Uses the official CLDR XML source at
https://github.com/unicode-org/cldr.git.

Usage:
    python3 extract_cldr.py                            # Fetch from GitHub, regenerate data/cldr/
    python3 extract_cldr.py --cldr-dir /path/to/cldr   # Use local CLDR repo clone
    python3 extract_cldr.py --tag release-46            # Use specific CLDR release tag
    python3 extract_cldr.py --locales de-DE ja-JP       # Extract specific locales only
"""

import json
import os
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import Request, urlopen, HTTPError, URLError

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "data" / "cldr"

INHERIT_MARKER = "↑↑↑"
CLDR_VERSION = "46"

# ---------------------------------------------------------------------------
# Locale inheritance chains (most specific → least specific)
# Based on CLDR parentLocales in supplementalData.xml
# ---------------------------------------------------------------------------
LOCALE_CHAINS = {
    "en-US":  ["en_US", "en", "root"],
    "de-DE":  ["de_DE", "de", "root"],
    "en-AU":  ["en_AU", "en_001", "en", "root"],
    "en-GB":  ["en_GB", "en_001", "en", "root"],
    "es-419": ["es_419", "es", "root"],
    "es-ES":  ["es_ES", "es", "root"],
    "fi-FI":  ["fi_FI", "fi", "root"],
    "fr-CA":  ["fr_CA", "fr", "root"],
    "fr-FR":  ["fr_FR", "fr", "root"],
    "it-IT":  ["it_IT", "it", "root"],
    "ja-JP":  ["ja_JP", "ja", "root"],
    "ko-KR":  ["ko_KR", "ko", "root"],
    "nl-NL":  ["nl_NL", "nl", "root"],
    "pt-BR":  ["pt_BR", "pt", "root"],
    "pt-PT":  ["pt_PT", "pt", "root"],
    "zh-CN":  ["zh_Hans_CN", "zh_Hans", "zh", "root"],
    "zh-HK":  ["zh_Hant_HK", "zh_Hant", "zh", "root"],
    "zh-TW":  ["zh_Hant_TW", "zh_Hant", "zh", "root"],
}

# Units relevant to software / telecom products
UNIT_KEYS = [
    "digital-petabyte", "digital-terabyte", "digital-terabit",
    "digital-gigabyte", "digital-gigabit", "digital-megabyte", "digital-megabit",
    "digital-kilobyte", "digital-kilobit", "digital-byte", "digital-bit",
    "duration-century", "duration-decade", "duration-year", "duration-quarter",
    "duration-month", "duration-week", "duration-day", "duration-hour",
    "duration-minute", "duration-second", "duration-millisecond",
    "duration-microsecond", "duration-nanosecond",
    "duration-night",
    "temperature-generic", "temperature-celsius", "temperature-fahrenheit",
    "temperature-kelvin",
]

# ============================================================================
# XML fetching / caching
# ============================================================================

_xml_cache: dict = {}


def _fetch_url(url: str) -> bytes | None:
    """Fetch a URL with retries."""
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "CLDR-Extract/1.0"})
            with urlopen(req, timeout=30) as resp:
                return resp.read()
        except HTTPError as e:
            if e.code == 404:
                return None
            if attempt == 2:
                print(f"    HTTP {e.code} for {url}")
                return None
        except (URLError, OSError) as e:
            if attempt == 2:
                print(f"    Network error for {url}: {e}")
                return None
    return None


def fetch_xml(cldr_dir: str | None, locale_file: str, tag: str = "main") -> ET.Element | None:
    """Fetch and parse a CLDR main XML file. Returns ET root or None."""
    cache_key = (cldr_dir, locale_file, tag)
    if cache_key in _xml_cache:
        return _xml_cache[cache_key]

    root = None
    if cldr_dir:
        path = Path(cldr_dir) / "common" / "main" / f"{locale_file}.xml"
        if path.exists():
            root = ET.parse(str(path)).getroot()
    else:
        url = f"https://raw.githubusercontent.com/unicode-org/cldr/{tag}/common/main/{locale_file}.xml"
        data = _fetch_url(url)
        if data:
            root = ET.fromstring(data)

    _xml_cache[cache_key] = root
    return root


def fetch_supplemental(cldr_dir: str | None, filename: str, tag: str = "main") -> ET.Element | None:
    """Fetch a CLDR supplemental XML file."""
    if cldr_dir:
        path = Path(cldr_dir) / "common" / "supplemental" / filename
        if path.exists():
            return ET.parse(str(path)).getroot()
        return None
    else:
        url = f"https://raw.githubusercontent.com/unicode-org/cldr/{tag}/common/supplemental/{filename}"
        data = _fetch_url(url)
        return ET.fromstring(data) if data else None


# ============================================================================
# XML extraction helpers
# ============================================================================

# Only strip ASCII whitespace to preserve Unicode whitespace chars like U+202F
# (NARROW NO-BREAK SPACE) which serve as valid number symbols (e.g., French grouping separator).
_ASCII_WS = " \t\n\r\f\v"


def _is_valid(text: str | None) -> bool:
    """Check if a text value is present and not the inheritance marker."""
    if text is None:
        return False
    stripped = text.strip(_ASCII_WS)
    return len(stripped) > 0 and INHERIT_MARKER not in stripped


def extract_number_symbols(xml_root: ET.Element) -> dict:
    """Extract number formatting symbols (latn number system)."""
    result = {}
    # Try latn-specific first, then any symbols block
    symbols = xml_root.find('.//numbers/symbols[@numberSystem="latn"]')
    if symbols is None:
        symbols = xml_root.find('.//numbers/symbols')
    if symbols is None:
        return result

    fields = [
        "decimal", "group", "list", "percentSign", "plusSign", "minusSign",
        "approximatelySign", "exponential", "superscriptingExponent",
        "perMille", "infinity", "nan", "timeSeparator",
    ]
    for field in fields:
        elem = symbols.find(field)
        if elem is not None and _is_valid(elem.text):
            result[field] = elem.text.strip(_ASCII_WS)

    return result


def extract_number_formats(xml_root: ET.Element) -> dict:
    """Extract standard decimal, percent, and currency format patterns."""
    result = {}

    # Standard decimal format (decimalFormatLength without type attr = standard)
    for df_len in xml_root.findall('.//numbers/decimalFormats[@numberSystem="latn"]/decimalFormatLength'):
        if df_len.get("type") is None:  # standard (no type attribute)
            pattern = df_len.find("decimalFormat/pattern")
            if pattern is not None and _is_valid(pattern.text):
                result["decimal_format"] = pattern.text.strip(_ASCII_WS)
            break

    # Percent format
    for pf_len in xml_root.findall('.//numbers/percentFormats[@numberSystem="latn"]/percentFormatLength'):
        if pf_len.get("type") is None:
            pattern = pf_len.find("percentFormat/pattern")
            if pattern is not None and _is_valid(pattern.text):
                result["percent_format"] = pattern.text.strip(_ASCII_WS)
            break

    # Currency format (standard type)
    for cf_len in xml_root.findall('.//numbers/currencyFormats[@numberSystem="latn"]/currencyFormatLength'):
        if cf_len.get("type") is None:
            cf = cf_len.find('currencyFormat[@type="standard"]')
            if cf is None:
                cf = cf_len.find("currencyFormat")
            if cf is not None:
                pattern = cf.find("pattern")
                if pattern is not None and _is_valid(pattern.text):
                    result["currency_format"] = pattern.text.strip(_ASCII_WS)
            break

    return result


def extract_date_formats(xml_root: ET.Element) -> dict:
    """Extract date/time format patterns from the gregorian calendar."""
    result = {}
    cal = xml_root.find('.//dates/calendars/calendar[@type="gregorian"]')
    if cal is None:
        return result

    # Date formats
    for length in ["full", "long", "medium", "short"]:
        df_len = cal.find(f'.//dateFormats/dateFormatLength[@type="{length}"]')
        if df_len is not None:
            # Skip if it's an alias
            if df_len.find("alias") is not None:
                continue
            pattern = df_len.find("dateFormat/pattern")
            if pattern is not None and _is_valid(pattern.text):
                result[f"date_{length}"] = pattern.text.strip(_ASCII_WS)

    # Time formats
    for length in ["full", "long", "medium", "short"]:
        tf_len = cal.find(f'.//timeFormats/timeFormatLength[@type="{length}"]')
        if tf_len is not None:
            if tf_len.find("alias") is not None:
                continue
            pattern = tf_len.find("timeFormat/pattern")
            if pattern is not None and _is_valid(pattern.text):
                result[f"time_{length}"] = pattern.text.strip(_ASCII_WS)

    return result


def extract_day_names(xml_root: ET.Element) -> dict:
    """Extract wide-format day names from the gregorian calendar."""
    result = {}
    cal = xml_root.find('.//dates/calendars/calendar[@type="gregorian"]')
    if cal is None:
        return result

    day_width = cal.find('.//days/dayContext[@type="format"]/dayWidth[@type="wide"]')
    if day_width is None or day_width.find("alias") is not None:
        return result

    for day_elem in day_width.findall("day"):
        day_type = day_elem.get("type")
        if day_type and _is_valid(day_elem.text):
            result[day_type] = day_elem.text.strip(_ASCII_WS)

    return result


def extract_month_names(xml_root: ET.Element) -> dict:
    """Extract wide-format month names from the gregorian calendar."""
    result = {}
    cal = xml_root.find('.//dates/calendars/calendar[@type="gregorian"]')
    if cal is None:
        return result

    month_width = cal.find('.//months/monthContext[@type="format"]/monthWidth[@type="wide"]')
    if month_width is None or month_width.find("alias") is not None:
        return result

    for month_elem in month_width.findall("month"):
        month_type = month_elem.get("type")
        if month_type and _is_valid(month_elem.text):
            result[month_type] = month_elem.text.strip(_ASCII_WS)

    return result


def extract_day_periods(xml_root: ET.Element) -> dict:
    """Extract AM/PM period markers from the gregorian calendar."""
    result = {}
    cal = xml_root.find('.//dates/calendars/calendar[@type="gregorian"]')
    if cal is None:
        return result

    # Try abbreviated first (most commonly used in UIs), then wide, then narrow
    for width in ["abbreviated", "wide", "narrow"]:
        dp_width = cal.find(
            f'.//dayPeriods/dayPeriodContext[@type="format"]'
            f'/dayPeriodWidth[@type="{width}"]'
        )
        if dp_width is None or dp_width.find("alias") is not None:
            continue

        for dp in dp_width.findall("dayPeriod"):
            dp_type = dp.get("type")
            if dp_type == "am" and _is_valid(dp.text) and "period_am" not in result:
                result["period_am"] = dp.text.strip(_ASCII_WS)
            elif dp_type == "pm" and _is_valid(dp.text) and "period_pm" not in result:
                result["period_pm"] = dp.text.strip(_ASCII_WS)

        if "period_am" in result and "period_pm" in result:
            break

    return result


def extract_units(xml_root: ET.Element, unit_keys: list) -> dict:
    """Extract short-form unit display names and patterns."""
    result = {}
    units_node = xml_root.find(".//units")
    if units_node is None:
        return result

    unit_length = units_node.find('unitLength[@type="short"]')
    if unit_length is None:
        return result

    for unit_key in unit_keys:
        unit_elem = unit_length.find(f'unit[@type="{unit_key}"]')
        if unit_elem is None:
            continue

        unit_data = {}
        dn = unit_elem.find("displayName")
        if dn is not None and _is_valid(dn.text):
            unit_data["displayName"] = dn.text.strip(_ASCII_WS)

        for pattern in unit_elem.findall("unitPattern"):
            count = pattern.get("count")
            if count and _is_valid(pattern.text):
                unit_data[count] = pattern.text.strip(_ASCII_WS)

        if unit_data:
            result[unit_key] = unit_data

    return result


# ============================================================================
# Inheritance resolution
# ============================================================================

def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base. Overlay values win."""
    result = dict(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def extract_all_from_xml(xml_root: ET.Element) -> dict:
    """Extract all relevant data from a single CLDR XML file."""
    data = {}

    symbols = extract_number_symbols(xml_root)
    if symbols:
        data["symbols"] = symbols

    num_fmts = extract_number_formats(xml_root)
    if num_fmts:
        data["number_formats"] = num_fmts

    date_fmts = extract_date_formats(xml_root)
    if date_fmts:
        data["date_formats"] = date_fmts

    days = extract_day_names(xml_root)
    if days:
        data["day_names"] = days

    months = extract_month_names(xml_root)
    if months:
        data["month_names"] = months

    periods = extract_day_periods(xml_root)
    if periods:
        data["day_periods"] = periods

    units = extract_units(xml_root, UNIT_KEYS)
    if units:
        data["units"] = units

    return data


def resolve_locale(cldr_dir: str | None, chain: list, tag: str = "main") -> tuple[dict, list]:
    """
    Resolve a locale's full data by walking the inheritance chain.

    Starts from root (least specific) and overlays more-specific locale data.
    Values that are ↑↑↑ or absent in a child file are filled by the parent.

    Returns (merged_data, list_of_source_files_that_contributed).
    """
    merged = {}
    actual_sources = []

    # Process from root (least specific) to child (most specific)
    for locale_file in reversed(chain):
        xml_root = fetch_xml(cldr_dir, locale_file, tag)
        if xml_root is None:
            continue

        actual_sources.append(f"{locale_file}.xml")
        data = extract_all_from_xml(xml_root)
        if data:
            merged = deep_merge(merged, data)

    return merged, actual_sources


# ============================================================================
# Plural rules (from supplemental data)
# ============================================================================

def extract_all_plural_rules(cldr_dir: str | None, tag: str = "main") -> dict:
    """Extract cardinal plural rules from supplemental/plurals.xml."""
    xml_root = fetch_supplemental(cldr_dir, "plurals.xml", tag)
    if xml_root is None:
        print("  WARNING: Could not fetch plurals.xml")
        return {}

    rules = {}
    for plural_rules in xml_root.findall('.//plurals[@type="cardinal"]/pluralRules'):
        locales_str = plural_rules.get("locales", "")
        locale_list = locales_str.split()

        rule_data = {}
        for rule in plural_rules.findall("pluralRule"):
            count = rule.get("count")
            if count and rule.text:
                rule_data[count] = rule.text.strip(_ASCII_WS)

        for loc in locale_list:
            rules[loc] = dict(rule_data)

    return rules


def get_plural_rules_for_locale(all_rules: dict, locale_tag: str) -> dict:
    """Look up plural rules for a target locale, trying fallback keys."""
    lang = locale_tag.split("-")[0]

    # Chinese script-specific lookups
    if locale_tag == "zh-CN":
        candidates = ["zh_Hans", "zh"]
    elif locale_tag in ("zh-TW", "zh-HK"):
        candidates = ["zh_Hant", "zh"]
    else:
        tag_underscore = locale_tag.replace("-", "_")
        candidates = [tag_underscore, lang]

    for key in candidates:
        if key in all_rules:
            return all_rules[key]

    return {"other": "@integer 0~15, 100, 1000, … @decimal 0.0~1.5, 10.0, 100.0, …"}


# ============================================================================
# Output formatting
# ============================================================================

def format_locale_json(
    locale_tag: str,
    merged: dict,
    sources: list,
    plural_rules: dict,
) -> dict:
    """Build the final output JSON for one locale in our schema."""
    symbols = merged.get("symbols", {})
    num_fmts = merged.get("number_formats", {})
    date_fmts = merged.get("date_formats", {})
    day_names = merged.get("day_names", {})
    month_names = merged.get("month_names", {})
    periods = merged.get("day_periods", {})
    units = merged.get("units", {})

    out = {
        "locale": locale_tag,
        "cldr_version": CLDR_VERSION,
        "cldr_sources": sources,
        "number_formats": {
            "decimal_format": num_fmts.get("decimal_format", "#,##0.###"),
            "percent_format": num_fmts.get("percent_format", "#,##0%"),
            "currency_format": num_fmts.get("currency_format", "¤#,##0.00"),
            "symbols": {
                "decimal": symbols.get("decimal", "."),
                "group": symbols.get("group", ","),
                "list": symbols.get("list", ";"),
                "percentSign": symbols.get("percentSign", "%"),
                "plusSign": symbols.get("plusSign", "+"),
                "minusSign": symbols.get("minusSign", "-"),
                "approximatelySign": symbols.get("approximatelySign", "≈"),
                "exponential": symbols.get("exponential", "E"),
                "superscriptingExponent": symbols.get("superscriptingExponent", "×"),
                "perMille": symbols.get("perMille", "‰"),
                "infinity": symbols.get("infinity", "∞"),
                "nan": symbols.get("nan", "NaN"),
                "timeSeparator": symbols.get("timeSeparator", ":"),
            },
        },
        "date_time_formats": {
            "date_full": date_fmts.get("date_full", ""),
            "date_long": date_fmts.get("date_long", ""),
            "date_medium": date_fmts.get("date_medium", ""),
            "date_short": date_fmts.get("date_short", ""),
            "time_full": date_fmts.get("time_full", ""),
            "time_long": date_fmts.get("time_long", ""),
            "time_medium": date_fmts.get("time_medium", ""),
            "time_short": date_fmts.get("time_short", ""),
            "day_names": {
                "sun": day_names.get("sun", ""),
                "mon": day_names.get("mon", ""),
                "tue": day_names.get("tue", ""),
                "wed": day_names.get("wed", ""),
                "thu": day_names.get("thu", ""),
                "fri": day_names.get("fri", ""),
                "sat": day_names.get("sat", ""),
            },
            "month_names": {
                str(i): month_names.get(str(i), "") for i in range(1, 13)
            },
            "period_am": periods.get("period_am", "AM"),
            "period_pm": periods.get("period_pm", "PM"),
        },
        "units": {},
        "plural_rules": plural_rules,
    }

    # Units: only include keys that have data
    for unit_key in UNIT_KEYS:
        if unit_key in units:
            out["units"][unit_key] = units[unit_key]

    return out


# ============================================================================
# Validation
# ============================================================================

def validate_output(data: dict, locale_tag: str) -> list:
    """Check for remaining ↑↑↑ markers or empty required fields."""
    issues = []

    def _walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                _walk(v, f"{path}.{k}")
        elif isinstance(obj, str):
            if INHERIT_MARKER in obj:
                issues.append(f"  UNRESOLVED ↑↑↑ at {path}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _walk(v, f"{path}[{i}]")

    _walk(data)

    # Check critical fields aren't empty
    symbols = data.get("number_formats", {}).get("symbols", {})
    for key in ["decimal", "group"]:
        if not symbols.get(key):
            issues.append(f"  MISSING number_formats.symbols.{key}")

    dtf = data.get("date_time_formats", {})
    for key in ["date_full", "date_short", "time_short"]:
        if not dtf.get(key):
            issues.append(f"  MISSING date_time_formats.{key}")

    day_names = dtf.get("day_names", {})
    if not day_names.get("mon"):
        issues.append("  MISSING date_time_formats.day_names.mon")

    month_names = dtf.get("month_names", {})
    if not month_names.get("1"):
        issues.append("  MISSING date_time_formats.month_names.1")

    return issues


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extract resolved CLDR locale data from the official Unicode CLDR repository."
    )
    parser.add_argument(
        "--cldr-dir",
        help="Path to a local clone of https://github.com/unicode-org/cldr.git. "
             "If omitted, XML files are fetched directly from GitHub.",
    )
    parser.add_argument(
        "--tag",
        default="main",
        help="Git branch or tag to fetch from (default: main). "
             "Use e.g. 'release-46' for a specific CLDR release.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory for JSON files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--locales",
        nargs="+",
        help="Extract only specific locales (default: all 18 target locales)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    target_locales = args.locales if args.locales else list(LOCALE_CHAINS.keys())

    source_label = args.cldr_dir if args.cldr_dir else f"github.com/unicode-org/cldr @ {args.tag}"
    print(f"CLDR source: {source_label}")
    print(f"Output dir:  {output_dir}")
    print(f"Locales:     {', '.join(target_locales)}")
    print()

    # --- Plural rules ---
    print("Fetching plural rules...")
    all_plural_rules = extract_all_plural_rules(args.cldr_dir, args.tag)
    print(f"  Cardinal rules found for {len(all_plural_rules)} locale keys\n")

    # --- Per-locale extraction ---
    summary = {
        "cldr_version": CLDR_VERSION,
        "cldr_source": "https://github.com/unicode-org/cldr.git",
        "total_locales": len(target_locales),
        "locales": {},
    }
    all_issues = {}

    for locale_tag in target_locales:
        chain = LOCALE_CHAINS.get(locale_tag)
        if not chain:
            print(f"[SKIP] Unknown locale: {locale_tag}")
            continue

        print(f"Processing {locale_tag}  ({' → '.join(chain)})...")
        merged, sources = resolve_locale(args.cldr_dir, chain, args.tag)
        plural = get_plural_rules_for_locale(all_plural_rules, locale_tag)

        result = format_locale_json(locale_tag, merged, sources, plural)

        # Validate
        issues = validate_output(result, locale_tag)
        if issues:
            all_issues[locale_tag] = issues
            for issue in issues:
                print(f"  WARNING: {issue}")

        # Write
        out_path = output_dir / f"{locale_tag}.json"
        with open(str(out_path), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  → {out_path.name}  (sources: {', '.join(sources)})")

        summary["locales"][locale_tag] = {
            "sources": sources,
            "sections": ["number_formats", "date_time_formats", "units", "plural_rules"],
        }

    # --- Summary ---
    summary_path = output_dir / "_summary.json"
    with open(str(summary_path), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nSummary → {summary_path.name}")

    # --- Final report ---
    print(f"\n{'=' * 60}")
    print(f"Extraction complete: {len(target_locales)} locales")
    if all_issues:
        total_warnings = sum(len(v) for v in all_issues.values())
        print(f"Warnings: {total_warnings} across {len(all_issues)} locales")
        for loc, issues in all_issues.items():
            for issue in issues:
                print(f"  {loc}: {issue}")
    else:
        print("Validation: ALL PASSED (no ↑↑↑ markers, no missing required fields)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
