# RC Core Products - Locale Data Index

## Supported Locales (18)

| BCP 47 Code | Language | Glossary File | Style Guide | CLDR Source |
|-------------|----------|---------------|-------------|-------------|
| en-US | English (US) | — (source) | — (source) | en.xml |
| de-DE | German (Germany) | de-de.json | DE-DE.json | de.xml + de_DE.xml |
| en-AU | English (Australia) | en-gb.json* | EN-UK.json* | en.xml + en_001.xml + en_AU.xml |
| en-GB | English (UK) | en-gb.json | EN-UK.json | en.xml + en_001.xml + en_GB.xml |
| es-419 | Spanish (Latin America) | es-419.json | ES-XL.json | es.xml + es_419.xml |
| es-ES | Spanish (Spain) | es-es.json | ES-ES.json | es.xml + es_ES.xml |
| fi-FI | Finnish | fi-fi.json | FI-FI.json | fi.xml + fi_FI.xml |
| fr-CA | French (Canada) | fr-ca.json | FR-CA.json | fr.xml + fr_CA.xml |
| fr-FR | French (France) | fr-fr.json | FR-FR.json | fr.xml + fr_FR.xml |
| it-IT | Italian | it-it.json | IT-IT.json | it.xml + it_IT.xml |
| ja-JP | Japanese | ja-jp.json | JA-JP.json | ja.xml + ja_JP.xml |
| ko-KR | Korean | ko-kr.json | KO-KR.json | ko.xml + ko_KR.xml |
| nl-NL | Dutch | nl-nl.json | NL-NL.json | nl.xml + nl_NL.xml |
| pt-BR | Portuguese (Brazil) | pt-br.json | PT-BR.json | pt.xml + pt_BR.xml |
| pt-PT | Portuguese (Portugal) | pt-pt.json | PT-PT.json | pt.xml + pt_PT.xml |
| zh-CN | Chinese Simplified | zh-cn.json | ZH-CN.json | zh.xml + zh_Hans.xml |
| zh-HK | Chinese (Hong Kong) | zh-tw.json* | ZH-TW.json* | zh.xml + zh_Hant.xml + zh_Hant_HK.xml |
| zh-TW | Chinese Traditional | zh-tw.json | ZH-TW.json | zh.xml + zh_Hant.xml |

*注：en-AU 使用 en-GB 的 glossary/style 作为基线；zh-HK 使用 zh-TW 的 glossary/style 作为基线。

## Data Sources

### 1. Glossary (术语库)
- **来源**: GitHub `Anna-SAP/FromJob828` → `output/glossaries/`
- **格式**: JSON，每个 locale 一个文件
- **字段**: term_id, source_term, target_term, part_of_speech, status, notes
- **总量**: ~40,000+ 条有效术语（18 语种合计）

### 2. Style Guides (翻译规范)
- **来源**: GitHub `Anna-SAP/FromJob828` → `output/styleguides/`
- **格式**: JSON，从 PDF 提取的结构化规则
- **字段**: rule_id, category, section, description, example_correct, example_incorrect
- **总量**: 2,281 条规则（18 语种合计）

### 3. CLDR (Unicode 区域标准)
- **来源**: GitHub `unicode-org/cldr` → `common/main/` + `common/supplemental/`
- **格式**: 从 XML 提取为 JSON
- **内容**: 数字格式、日期时间格式、星期/月份名称、复数规则、单位翻译
- **覆盖**: 18 个目标 locale 全部覆盖

## Locale Pair Relationships (需重点审查差异的语种对)

| Pair | Key Differences |
|------|----------------|
| pt-BR / pt-PT | 动名词 vs 不定式偏好，正式程度，特定术语选择 |
| zh-CN / zh-TW / zh-HK | 简体/繁体字符，术语习惯（如 "视频" vs "影片"） |
| es-419 / es-ES | voseo 用法，区域术语差异（如 "computadora" vs "ordenador"） |
| fr-CA / fr-FR | 拼写变体，anglicism 接受度，正式程度 |
| en-GB / en-AU | 拼写差异微小（-ise/-ize），日期格式 DD/MM/YYYY |
