#!/usr/bin/env python3
"""
RC Translation Checker - Batch Audit Tool
Parses a JSON translation file and cross-references against glossary, style rules, and CLDR data.

Usage:
  python3 audit_translations.py <input_json_file> [--locale <locale>] [--output <output_file>]

Input JSON format expected:
  {
    "key1": {
      "en-US": "Source text",
      "de-DE": "German translation",
      "ja-JP": "Japanese translation",
      ...
    },
    ...
  }
  
  OR flat format:
  {
    "en-US": { "key1": "text1", "key2": "text2" },
    "de-DE": { "key1": "text1", "key2": "text2" },
    ...
  }
"""

import json
import os
import sys
import re
import argparse

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSSARY_DIR = os.path.join(SKILL_DIR, "data", "glossaries")
STYLE_DIR = os.path.join(SKILL_DIR, "data", "styleguides")
CLDR_DIR = os.path.join(SKILL_DIR, "data", "cldr")

SUPPORTED_LOCALES = [
    "en-US", "de-DE", "en-AU", "en-GB", "es-419", "es-ES",
    "fi-FI", "fr-CA", "fr-FR", "it-IT", "ja-JP", "ko-KR",
    "nl-NL", "pt-BR", "pt-PT", "zh-CN", "zh-HK", "zh-TW"
]

GLOSSARY_MAP = {
    "de-DE": "de-de", "en-AU": "en-gb", "en-GB": "en-gb",
    "es-419": "es-419", "es-ES": "es-es", "fi-FI": "fi-fi",
    "fr-CA": "fr-ca", "fr-FR": "fr-fr", "it-IT": "it-it",
    "ja-JP": "ja-jp", "ko-KR": "ko-kr", "nl-NL": "nl-nl",
    "pt-BR": "pt-br", "pt-PT": "pt-pt", "zh-CN": "zh-cn",
    "zh-HK": "zh-tw", "zh-TW": "zh-tw",
}


def load_json(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_glossary_index(locale):
    """Load glossary as a source_term -> target_term lookup dict.

    Includes terms with status "VALID" as well as terms with status=null,
    which represent valid entries that haven't been explicitly marked.
    Only excludes terms with explicit non-VALID statuses (e.g. "OBSOLETE").
    """
    code = GLOSSARY_MAP.get(locale)
    if not code:
        return {}
    data = load_json(os.path.join(GLOSSARY_DIR, f"{code}.json"))
    if not data:
        return {}
    index = {}
    for t in data.get("terms", []):
        status = t.get("status")
        # Include VALID and null-status terms; skip explicitly invalid ones
        if status not in (None, "VALID"):
            continue
        src = t.get("source_term", "").lower().strip()
        if src:
            index[src] = {
                "target": t.get("target_term", ""),
                "pos": t.get("part_of_speech", ""),
                "notes": t.get("notes", ""),
            }
    return index


def detect_format(data):
    """Detect if JSON is key-first or locale-first format."""
    first_key = next(iter(data))
    first_val = data[first_key]
    if isinstance(first_val, dict):
        sub_keys = list(first_val.keys())
        # Check if sub-keys look like locale codes
        if any(k in SUPPORTED_LOCALES for k in sub_keys):
            return "key_first"  # { "key1": { "en-US": "...", "ja-JP": "..." } }
        # Check if first key looks like a locale
        if first_key in SUPPORTED_LOCALES:
            return "locale_first"  # { "en-US": { "key1": "..." }, "ja-JP": { "key1": "..." } }
    return "unknown"


def normalize_to_key_first(data, fmt):
    """Normalize to key-first format: { key: { locale: text } }."""
    if fmt == "key_first":
        return data
    elif fmt == "locale_first":
        result = {}
        for locale, entries in data.items():
            if isinstance(entries, dict):
                for key, text in entries.items():
                    if key not in result:
                        result[key] = {}
                    result[key][locale] = text
        return result
    return data


def check_placeholder_consistency(source, target, key):
    """Check that placeholders in source exist in target."""
    issues = []
    # Common placeholder patterns: {0}, {name}, %s, %d, {{var}}, $t(key)
    patterns = [
        r'\{[^}]+\}',      # {placeholder}
        r'%[sd]',           # printf-style
        r'\$t\([^)]+\)',    # i18next interpolation
        r'<[^>]+>',         # HTML tags
    ]
    for pat in patterns:
        src_matches = set(re.findall(pat, source))
        tgt_matches = set(re.findall(pat, target))
        missing = src_matches - tgt_matches
        extra = tgt_matches - src_matches
        if missing:
            issues.append({
                "type": "missing_placeholder",
                "detail": f"Placeholders in source but missing in target: {missing}",
                "severity": "HIGH",
            })
        if extra:
            issues.append({
                "type": "extra_placeholder",
                "detail": f"Extra placeholders in target not in source: {extra}",
                "severity": "MEDIUM",
            })
    return issues


def check_glossary_compliance(source, target, glossary_index, locale):
    """Check if known glossary terms are translated correctly.

    Uses longest-match-first strategy: compound terms (e.g. "AI Agent") are
    evaluated before their component words (e.g. "agent"), so that a correct
    compound translation does not generate false-positive single-word mismatches.
    """
    issues = []
    source_lower = source.lower()
    # Strip placeholders from source before matching
    source_clean = re.sub(r'\{[^}]+\}', ' ', source_lower)
    source_clean = re.sub(r'%[sd]', ' ', source_clean)

    # Sort terms by length descending (longest / most-specific first)
    sorted_terms = sorted(glossary_index.items(), key=lambda x: len(x[0]), reverse=True)

    # Track words already "consumed" by a correctly-matched compound term
    consumed_words = set()

    for src_term, entry in sorted_terms:
        # Skip very short terms (< 3 chars) to avoid false positives
        if len(src_term) < 3:
            continue

        term_words = src_term.lower().split()

        # If every word in this term is already consumed by a longer match, skip
        if all(w in consumed_words for w in term_words):
            continue

        # Use word boundary matching
        pattern = r'\b' + re.escape(src_term) + r'\b'
        if re.search(pattern, source_clean, re.IGNORECASE):
            expected = entry["target"]
            if expected and expected.lower() not in target.lower():
                issues.append({
                    "type": "glossary_mismatch",
                    "detail": f"Term '{src_term}' should be '{expected}' per glossary, but not found in translation",
                    "expected": expected,
                    "severity": "MEDIUM",
                    "notes": entry.get("notes", ""),
                })
            else:
                # Term matched and translation is correct — consume its words
                # so shorter sub-terms don't raise spurious mismatches
                for w in term_words:
                    consumed_words.add(w)
    return issues


def check_length_ratio(source, target, locale):
    """Flag translations that are suspiciously long or short relative to source."""
    issues = []
    if not source or not target:
        return issues
    
    ratio = len(target) / len(source) if len(source) > 0 else 0
    
    # CJK languages tend to be shorter
    cjk_locales = {"ja-JP", "ko-KR", "zh-CN", "zh-HK", "zh-TW"}
    
    if locale in cjk_locales:
        if ratio > 1.5:
            issues.append({
                "type": "length_expansion",
                "detail": f"CJK translation is {ratio:.1f}x source length (unusual)",
                "severity": "LOW",
            })
    else:
        if ratio > 2.5:
            issues.append({
                "type": "length_expansion",
                "detail": f"Translation is {ratio:.1f}x source length — potential UI overflow",
                "severity": "MEDIUM",
            })
        elif ratio < 0.3 and len(source) > 10:
            issues.append({
                "type": "length_contraction",
                "detail": f"Translation is only {ratio:.1f}x source length — possible truncation or missing content",
                "severity": "MEDIUM",
            })
    return issues


def check_untranslated(source, target, locale):
    """Check if target is identical to source (possible untranslated string)."""
    if locale == "en-US":
        return []
    if source == target and len(source) > 3:
        # Skip if it looks like a proper noun or technical term
        if not re.match(r'^[A-Z][a-z]+$', source) and not re.match(r'^[A-Z_]+$', source):
            return [{
                "type": "untranslated",
                "detail": f"Target is identical to en-US source — may be untranslated",
                "severity": "HIGH",
            }]
    return []


def audit_file(input_path, target_locales=None):
    """Run full audit on a translation JSON file."""
    data = load_json(input_path)
    if not data:
        return {"error": f"Cannot load {input_path}"}
    
    fmt = detect_format(data)
    if fmt == "unknown":
        return {"error": "Unrecognized JSON format. Expected key-first or locale-first structure."}
    
    normalized = normalize_to_key_first(data, fmt)
    
    # Determine which locales to audit
    all_locales = set()
    for key_data in normalized.values():
        if isinstance(key_data, dict):
            all_locales.update(key_data.keys())
    
    if target_locales:
        audit_locales = [l for l in target_locales if l in all_locales and l != "en-US"]
    else:
        audit_locales = [l for l in all_locales if l in SUPPORTED_LOCALES and l != "en-US"]
    
    # Load glossaries
    glossaries = {}
    for loc in audit_locales:
        glossaries[loc] = load_glossary_index(loc)
    
    # Run checks
    results = {
        "input_file": input_path,
        "format_detected": fmt,
        "total_keys": len(normalized),
        "locales_audited": audit_locales,
        "issues": [],
        "summary": {},
    }
    
    issue_counts = {}
    
    for key, translations in normalized.items():
        if not isinstance(translations, dict):
            continue
        source = translations.get("en-US", "")
        if not source:
            continue
        
        for loc in audit_locales:
            target = translations.get(loc, "")
            if not target:
                results["issues"].append({
                    "key": key,
                    "locale": loc,
                    "type": "missing_translation",
                    "detail": "No translation provided",
                    "severity": "HIGH",
                    "source": source,
                    "target": "",
                })
                issue_counts[loc] = issue_counts.get(loc, 0) + 1
                continue
            
            # Run all checks
            all_issues = []
            all_issues.extend(check_placeholder_consistency(source, target, key))
            all_issues.extend(check_glossary_compliance(source, target, glossaries.get(loc, {}), loc))
            all_issues.extend(check_length_ratio(source, target, loc))
            all_issues.extend(check_untranslated(source, target, loc))
            
            for issue in all_issues:
                issue["key"] = key
                issue["locale"] = loc
                issue["source"] = source
                issue["target"] = target
                results["issues"].append(issue)
                issue_counts[loc] = issue_counts.get(loc, 0) + 1
    
    # Build summary
    severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    type_counts = {}
    for issue in results["issues"]:
        sev = issue.get("severity", "LOW")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        itype = issue.get("type", "other")
        type_counts[itype] = type_counts.get(itype, 0) + 1
    
    results["summary"] = {
        "total_issues": len(results["issues"]),
        "by_severity": severity_counts,
        "by_type": type_counts,
        "by_locale": issue_counts,
    }
    
    return results


def main():
    parser = argparse.ArgumentParser(description="RC Translation Audit Tool")
    parser.add_argument("input", help="Path to JSON translation file")
    parser.add_argument("--locale", nargs="+", help="Specific locale(s) to audit")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--severity", choices=["HIGH", "MEDIUM", "LOW"], help="Filter by minimum severity")
    
    args = parser.parse_args()
    
    results = audit_file(args.input, args.locale)
    
    if args.severity:
        severity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_sev = severity_order[args.severity]
        results["issues"] = [
            i for i in results["issues"]
            if severity_order.get(i.get("severity", "LOW"), 0) >= min_sev
        ]
    
    output = json.dumps(results, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Audit results saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
