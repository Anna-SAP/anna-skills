#!/usr/bin/env python3
"""
RC Translation Checker - Locale Data Lookup Tool
Retrieves glossary terms, style rules, and CLDR standards for a given locale.

Usage:
  python3 lookup_locale.py <locale_code> [--section glossary|style|cldr|all] [--term <search_term>] [--limit N]

Examples:
  python3 lookup_locale.py ja-JP --section all
  python3 lookup_locale.py de-DE --section glossary --term "voicemail"
  python3 lookup_locale.py zh-CN --section style --limit 20
  python3 lookup_locale.py fr-FR --section cldr
"""

import json
import os
import sys
import argparse

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSSARY_DIR = os.path.join(SKILL_DIR, "data", "glossaries")
STYLE_DIR = os.path.join(SKILL_DIR, "data", "styleguides")
CLDR_DIR = os.path.join(SKILL_DIR, "data", "cldr")

# Locale code normalization map
LOCALE_NORMALIZE = {
    # Glossary files use lowercase
    "glossary": {
        "en-US": None,  # No glossary for en-US (it's the source)
        "de-DE": "de-de", "en-AU": "en-gb", "en-GB": "en-gb",
        "es-419": "es-419", "es-ES": "es-es", "fi-FI": "fi-fi",
        "fr-CA": "fr-ca", "fr-FR": "fr-fr", "it-IT": "it-it",
        "ja-JP": "ja-jp", "ko-KR": "ko-kr", "nl-NL": "nl-nl",
        "pt-BR": "pt-br", "pt-PT": "pt-pt", "zh-CN": "zh-cn",
        "zh-HK": "zh-tw", "zh-TW": "zh-tw",
    },
    # Style guide files use uppercase
    "style": {
        "en-US": None,
        "de-DE": "DE-DE", "en-AU": "EN-UK", "en-GB": "EN-UK",
        "es-419": "ES-XL", "es-ES": "ES-ES", "fi-FI": "FI-FI",
        "fr-CA": "FR-CA", "fr-FR": "FR-FR", "it-IT": "IT-IT",
        "ja-JP": "JA-JP", "ko-KR": "KO-KR", "nl-NL": "NL-NL",
        "pt-BR": "PT-BR", "pt-PT": "PT-PT", "zh-CN": "ZH-CN",
        "zh-HK": "ZH-TW", "zh-TW": "ZH-TW",
    },
}

SUPPORTED_LOCALES = [
    "en-US", "de-DE", "en-AU", "en-GB", "es-419", "es-ES",
    "fi-FI", "fr-CA", "fr-FR", "it-IT", "ja-JP", "ko-KR",
    "nl-NL", "pt-BR", "pt-PT", "zh-CN", "zh-HK", "zh-TW"
]


def load_json(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_glossary(locale, search_term=None, limit=50):
    """Load glossary terms for a locale, optionally filtering by search term."""
    code = LOCALE_NORMALIZE["glossary"].get(locale)
    if code is None:
        return {"info": f"No glossary available for {locale} (source language or mapped to another locale)"}
    
    filepath = os.path.join(GLOSSARY_DIR, f"{code}.json")
    data = load_json(filepath)
    if not data:
        return {"error": f"Glossary file not found: {filepath}"}
    
    terms = data.get("terms", [])
    
    if search_term:
        search_lower = search_term.lower()
        terms = [t for t in terms if 
                 search_lower in t.get("source_term", "").lower() or
                 search_lower in t.get("target_term", "").lower() or
                 search_lower in (t.get("definition") or "").lower() or
                 search_lower in (t.get("notes") or "").lower()]
    
    # Filter to VALID terms only
    terms = [t for t in terms if t.get("status") == "VALID"]
    
    total = len(terms)
    terms = terms[:limit]
    
    return {
        "locale": locale,
        "glossary_file": code,
        "total_matching_terms": total,
        "showing": len(terms),
        "terms": terms,
    }


def get_style_rules(locale, limit=50):
    """Load style guide rules for a locale."""
    code = LOCALE_NORMALIZE["style"].get(locale)
    if code is None:
        return {"info": f"No style guide for {locale}"}
    
    filepath = os.path.join(STYLE_DIR, f"{code}.json")
    data = load_json(filepath)
    if not data:
        return {"error": f"Style guide file not found: {filepath}"}
    
    rules = data.get("rules", [])
    total = len(rules)
    rules = rules[:limit]
    
    return {
        "locale": locale,
        "style_file": code,
        "source_pdf": data.get("source", ""),
        "total_rules": total,
        "showing": len(rules),
        "rules": rules,
    }


def get_cldr(locale):
    """Load CLDR locale standards."""
    filepath = os.path.join(CLDR_DIR, f"{locale}.json")
    data = load_json(filepath)
    if not data:
        return {"error": f"CLDR data not found for {locale}"}
    return data


def get_all(locale, search_term=None, limit=30):
    """Get combined overview for a locale."""
    result = {
        "locale": locale,
        "glossary_summary": None,
        "style_summary": None,
        "cldr": None,
    }
    
    g = get_glossary(locale, search_term, limit)
    result["glossary_summary"] = {
        "total_terms": g.get("total_matching_terms", 0),
        "sample_terms": g.get("terms", [])[:10],
    } if "terms" in g else g
    
    s = get_style_rules(locale, limit)
    result["style_summary"] = {
        "source": s.get("source_pdf", ""),
        "total_rules": s.get("total_rules", 0),
        "categories": {},
    }
    if "rules" in s:
        cats = {}
        for r in s["rules"]:
            cat = r.get("category", "other")
            cats[cat] = cats.get(cat, 0) + 1
        result["style_summary"]["categories"] = cats
    
    result["cldr"] = get_cldr(locale)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="RC Translation Checker - Locale Data Lookup")
    parser.add_argument("locale", help=f"Locale code. Supported: {', '.join(SUPPORTED_LOCALES)}")
    parser.add_argument("--section", choices=["glossary", "style", "cldr", "all"], default="all")
    parser.add_argument("--term", help="Search term (for glossary lookup)")
    parser.add_argument("--limit", type=int, default=50, help="Max results to return")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.locale not in SUPPORTED_LOCALES:
        print(f"ERROR: Unsupported locale '{args.locale}'")
        print(f"Supported: {', '.join(SUPPORTED_LOCALES)}")
        sys.exit(1)
    
    if args.section == "glossary":
        result = get_glossary(args.locale, args.term, args.limit)
    elif args.section == "style":
        result = get_style_rules(args.locale, args.limit)
    elif args.section == "cldr":
        result = get_cldr(args.locale)
    else:
        result = get_all(args.locale, args.term, args.limit)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
