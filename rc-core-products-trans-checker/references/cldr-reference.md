# CLDR i18n Quick Reference for Translation Auditing

## Key CLDR Concepts for LQA

### 1. Number Formatting
Each locale has specific rules for decimal separators, grouping separators, and currency display:

| Locale | Decimal | Grouping | Example (1,234.56) | Currency |
|--------|---------|----------|---------------------|----------|
| en-US | . | , | 1,234.56 | $1,234.56 |
| de-DE | , | . | 1.234,56 | 1.234,56 € |
| fr-FR | , | (space) | 1 234,56 | 1 234,56 € |
| fr-CA | , | (space) | 1 234,56 | 1 234,56 $ |
| ja-JP | . | , | 1,234.56 | ¥1,235 |
| ko-KR | . | , | 1,234.56 | ₩1,235 |
| pt-BR | , | . | 1.234,56 | R$ 1.234,56 |
| zh-CN | . | , | 1,234.56 | ¥1,234.56 |

### 2. Date/Time Formats
Common pitfalls: month/day order, 12h vs 24h clock, era markers.

| Locale | Short Date | Long Date | Time |
|--------|-----------|-----------|------|
| en-US | M/d/yy | MMMM d, y | h:mm a |
| en-GB | dd/MM/y | d MMMM y | HH:mm |
| de-DE | dd.MM.yy | d. MMMM y | HH:mm |
| fr-FR | dd/MM/y | d MMMM y | HH:mm |
| ja-JP | y/MM/dd | y年M月d日 | H:mm |
| ko-KR | y. M. d. | y년 M월 d일 | a h:mm |
| zh-CN | y/M/d | y年M月d日 | HH:mm |
| zh-TW | y/M/d | y年M月d日 | HH:mm |

### 3. Plural Rules (ICU)
Languages vary in how many plural forms they require:

| Category | Languages | Forms |
|----------|-----------|-------|
| No plural | ja, ko, zh | 1 form (other) |
| Simple (sg/pl) | de, en, es, fr, it, nl, pt | 2 forms (one, other) |
| Complex | fi | one, other (+ partitive in some contexts) |

### 4. Common Audit Flags

**Number format violations**: Check that UI strings displaying numbers use locale-appropriate separators.

**Date format violations**: Ensure date/time displays match CLDR patterns for the locale.

**Placeholder integrity**: Variables like {0}, {count}, %s must be preserved exactly in all translations.

**DNT (Do Not Translate) terms**: Product names, brand names, and technical identifiers must remain in their original form.

**UI length constraints**: German and Finnish typically expand 30-40% vs English; CJK may contract 20-30%.

### 5. BCP 47 Tag Validation
Ensure locale tags follow proper format:
- `language-region` (e.g., `pt-BR`)
- `language-script-region` for disambiguation (e.g., `zh-Hans-CN`)
- IANA subtag registry is authoritative

### 6. ICU Message Format Patterns
When translations contain ICU patterns, verify:
- `{count, plural, one {# item} other {# items}}` — all required plural categories present
- `{gender, select, male {He} female {She} other {They}}` — all branches present
- Nested patterns maintain correct brace matching
