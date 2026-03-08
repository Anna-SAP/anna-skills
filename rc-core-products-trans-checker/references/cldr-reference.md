# CLDR i18n Quick Reference for Translation Auditing

Data source: [unicode-org/cldr](https://github.com/unicode-org/cldr.git) (CLDR 46)
Regenerate: `python3 scripts/extract_cldr.py`

## Key CLDR Concepts for LQA

### 1. Number Formatting
Each locale has specific rules for decimal separators, grouping separators, and currency display:

| Locale | Decimal | Grouping | Example (1,234.56) | Currency Pattern |
|--------|---------|----------|---------------------|------------------|
| en-US | . | , | 1,234.56 | ¤#,##0.00 |
| de-DE | , | . | 1.234,56 | #,##0.00 ¤ |
| fr-FR | , | (NNBSP) | 1 234,56 | #,##0.00 ¤ |
| fr-CA | , | (NBSP) | 1 234,56 | #,##0.00 ¤ |
| fi-FI | , | (NBSP) | 1 234,56 | #,##0.00 ¤ |
| es-ES | , | . | 1.234,56 | #,##0.00 ¤ |
| es-419 | . | , | 1,234.56 | ¤#,##0.00 |
| it-IT | , | . | 1.234,56 | #,##0.00 ¤ |
| nl-NL | , | . | 1.234,56 | ¤ #,##0.00 |
| ja-JP | . | , | 1,234.56 | ¤#,##0.00 |
| ko-KR | . | , | 1,234.56 | ¤#,##0.00 |
| pt-BR | , | . | 1.234,56 | ¤ #,##0.00 |
| pt-PT | , | (NBSP) | 1 234,56 | #,##0.00 ¤ |
| zh-CN | . | , | 1,234.56 | ¤#,##0.00 |
| zh-TW | . | , | 1,234.56 | ¤#,##0.00 |
| zh-HK | . | , | 1,234.56 | ¤#,##0.00 |

> NNBSP = U+202F (Narrow No-Break Space), NBSP = U+00A0 (No-Break Space)

### 2. Date/Time Formats
Common pitfalls: month/day order, 12h vs 24h clock, separator style.

| Locale | Short Date | Long Date | Time (short) | Clock |
|--------|-----------|-----------|--------------|-------|
| en-US | M/d/yy | MMMM d, y | h:mm a | 12h |
| en-GB | dd/MM/y | d MMMM y | HH:mm | 24h |
| en-AU | d/M/yy | d MMMM y | h:mm a | 12h |
| de-DE | dd.MM.yy | d. MMMM y | HH:mm | 24h |
| fr-FR | dd/MM/y | d MMMM y | HH:mm | 24h |
| fr-CA | y-MM-dd | d MMMM y | HH 'h' mm | 24h |
| es-ES | d/M/yy | d MMMM y | H:mm | 24h |
| es-419 | d/M/yy | d MMMM y | h:mm a | 12h |
| fi-FI | d.M.y | d. MMMM y | H.mm | 24h |
| it-IT | dd/MM/yy | d MMMM y | HH:mm | 24h |
| ja-JP | y/MM/dd | y年M月d日 | H:mm | 24h |
| ko-KR | yy. M. d. | y년 M월 d일 | a h:mm | 12h |
| nl-NL | dd-MM-y | d MMMM y | HH:mm | 24h |
| pt-BR | dd/MM/y | d 'de' MMMM 'de' y | HH:mm | 24h |
| pt-PT | dd/MM/y | d 'de' MMMM 'de' y | HH:mm | 24h |
| zh-CN | y/M/d | y年M月d日 | HH:mm | 24h |
| zh-TW | y/M/d | y年M月d日 | HH:mm | 24h |
| zh-HK | d/M/y | y年M月d日 | ah:mm | 12h |

### 3. AM/PM Markers

| Locale | AM | PM | Notes |
|--------|----|----|-------|
| en-US | AM | PM | |
| en-AU | am | pm | Lowercase |
| en-GB | am | pm | Lowercase |
| de-DE | AM | PM | Rarely used (24h clock) |
| fr-FR | AM | PM | Rarely used (24h clock) |
| ja-JP | 午前 | 午後 | Prefix style (午前10:00) |
| ko-KR | 오전 | 오후 | Prefix style (오전 10:00) |
| zh-CN | 上午 | 下午 | Rarely used (24h clock) |
| zh-TW | 上午 | 下午 | |
| zh-HK | 上午 | 下午 | Prefix style (上午10:00) |

### 4. Plural Rules (ICU)
Languages vary in how many plural forms they require:

| Category | Languages | Forms |
|----------|-----------|-------|
| No plural | ja, ko, zh | 1 form (other) |
| Simple (sg/pl) | de, en, es, fr, it, nl, pt | 2 forms (one, other) |
| Complex | fi | one, other (+ partitive in some contexts) |

### 5. Common Audit Flags

**Number format violations**: Check that UI strings displaying numbers use locale-appropriate separators. Pay special attention to grouping separators that are whitespace characters (fr-FR U+202F, fi-FI/fr-CA/pt-PT U+00A0).

**Date format violations**: Ensure date/time displays match CLDR patterns for the locale. Watch for month/day order (M/d vs d/M), clock format (12h vs 24h), and separator style (`.` vs `/` vs `-`).

**Placeholder integrity**: Variables like {0}, {count}, %s must be preserved exactly in all translations.

**DNT (Do Not Translate) terms**: Product names, brand names, and technical identifiers must remain in their original form.

**UI length constraints**: German and Finnish typically expand 30-40% vs English; CJK may contract 20-30%.

### 6. BCP 47 Tag Validation
Ensure locale tags follow proper format:
- `language-region` (e.g., `pt-BR`)
- `language-script-region` for disambiguation (e.g., `zh-Hans-CN`)
- IANA subtag registry is authoritative

### 7. ICU Message Format Patterns
When translations contain ICU patterns, verify:
- `{count, plural, one {# item} other {# items}}` — all required plural categories present
- `{gender, select, male {He} female {She} other {They}}` — all branches present
- Nested patterns maintain correct brace matching
