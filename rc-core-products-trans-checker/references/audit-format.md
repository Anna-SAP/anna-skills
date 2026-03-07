# Translation Audit Report Format

## Output Structure

The audit report follows a standardized format for consistency across all RC product translation reviews.

## Issue Severity Levels

- **HIGH**: Must fix before release — missing translations, broken placeholders, critical terminology errors
- **MEDIUM**: Should fix — glossary mismatches, significant length expansion, ambiguous abbreviations
- **LOW**: Nice to fix — minor style inconsistencies, suboptimal wording, length ratio anomalies

## Issue Types

| Type | Description | Severity |
|------|-------------|----------|
| missing_translation | No translation provided for a key | HIGH |
| missing_placeholder | Source placeholder absent from translation | HIGH |
| untranslated | Target identical to en-US source | HIGH |
| glossary_mismatch | Term doesn't match approved glossary | MEDIUM |
| extra_placeholder | Placeholder in target not in source | MEDIUM |
| length_expansion | Translation significantly longer than source | MEDIUM |
| length_contraction | Translation significantly shorter than source | MEDIUM |
| cldr_violation | Number/date/time format doesn't match locale standard | MEDIUM |
| style_violation | Violates locale-specific style guide rule | LOW-MEDIUM |
| disambiguation | Ambiguous abbreviation or context-dependent term | MEDIUM |

## Report Template (Markdown)

```markdown
# Translation Audit Report

## Summary
- **File**: [filename]
- **Date**: [audit date]
- **Locales audited**: [list]
- **Total keys**: [N]
- **Total issues**: [N] (HIGH: N, MEDIUM: N, LOW: N)

## Critical Issues (HIGH)
| Key | Locale | Issue | Source | Target | Fix |
|-----|--------|-------|--------|--------|-----|

## Recommended Fixes (MEDIUM)
| Key | Locale | Issue | Source | Target | Fix |

## Root Cause Analysis (RCA)
For each issue pattern:
1. What caused it
2. Which locales affected
3. Systemic fix recommendation

## Locale-Specific Notes
[Per-locale observations and recommendations]
```
