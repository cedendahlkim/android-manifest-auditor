# Android Manifest Auditor

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-15%20passing-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-95%25-brightgreen.svg)](tests/)

Ett kraftfullt CLI-verktyg för Android-utvecklare som snabbt granskar `AndroidManifest.xml` och flaggar vanliga misstag som ofta upptäcks för sent i utvecklingen.

## ✨ Funktioner

- **🔍 Manifest parsing**: Läser ett eller flera manifestfiler
- **🔗 Deep link audit**: Kontrollerar `VIEW`-intent filters och App Links-konfiguration
- **🚪 Exported audit**: Varnar om komponenter med intent filters saknar `android:exported`
- **🔐 Permission hints**: Markerar känsliga permissions och ger UX-råd
- **📱 Auto-discovery**: Hittar automatiskt manifestfiler i Android-projekt
- **📊 Multiple outputs**: Human readable, JSON, och SARIF-format
- **🚀 CI-integration**: Fullt stöd för GitHub Actions med SARIF

## 🚀 Snabbstart

### Installation

```bash
pip install android-manifest-auditor
```

### Användning

```bash
# Granska specifik manifestfil
manifest-audit app/src/main/AndroidManifest.xml

# Auto-discovery i Android-projekt
manifest-audit

# JSON-output för CI
manifest-audit --json app/src/main/AndroidManifest.xml

# SARIF för GitHub integration
manifest-audit --sarif app/src/main/AndroidManifest.xml
```

## 📋 Exempel på fynd

- `VIEW`-intent filter med `data` men utan `BROWSABLE`
- deep link utan `DEFAULT`
- `http`/`https`-links utan `autoVerify="true"`
- komponent med intent-filter men utan `android:exported`
- duplicate deep link-konfigurationer
- dangerous permission utan tydlig UX-kommentar

## 🔧 GitHub Actions Integration

Lägg till i din `.github/workflows/manifest-audit.yml`:

```yaml
name: Android Manifest Audit

on:
  push:
    paths: [ '**/AndroidManifest.xml' ]
  pull_request:
    paths: [ '**/AndroidManifest.xml' ]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    - run: pip install android-manifest-auditor
    - run: |
        manifest-audit --sarif > audit-results.sarif
    - uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: audit-results.sarif
```

## 📊 Output-format

### Human-readable
```
Android Manifest Audit
========================
Manifestfiler: 1
Fel: 2 | Varningar: 1 | Info: 2

✗ [ERROR] deeplink.missing_browsable_category
  Fil: app/src/main/AndroidManifest.xml
  Element: intent-filter
  Komponent: .MainActivity
  Deep link-intent filter saknar BROWSABLE-kategorin.
```

### JSON
```json
{
  "manifests": ["app/src/main/AndroidManifest.xml"],
  "summary": {"errors": 2, "warnings": 1, "info": 2, "total": 5},
  "findings": [...]
}
```

### SARIF
Fullt kompatibelt med GitHub Advanced Security och code scanning.

## 🧪 Utveckling

```bash
# Installera med test-dependencies
pip install -e ".[test]"

# Kör tester
pytest

# Kör med coverage
pytest --cov=manifest_auditor
```

## 📈 Regelkollning

Verktyget kontrollerar följande regler:

### Deep Links
- `deeplink.missing_default_category` - Saknar DEFAULT-kategori
- `deeplink.missing_browsable_category` - Saknar BROWSABLE-kategori  
- `deeplink.missing_scheme` - Saknar android:scheme
- `deeplink.missing_path_specification` - HTTP/HTTPS utan path
- `deeplink.invalid_host_characters` - Ogiltiga tecken i host
- `deeplink.duplicate_host_scheme` - Duplicate konfigurationer
- `deeplink.http_without_autoverify` - Saknar autoVerify

### Komponenter
- `component.missing_exported` - Intent-filter utan exported-attribut

### Permissions
- `permission.rationale_hint` - Känsliga permissions
- `permission.internet_note` - INTERNET permission notering

### Manifest
- `manifest.missing_application` - Saknar application-element
- `manifest.empty_package` - Tomt package-attribut
- `manifest.parse_error` - XML-parsefel
- `file.not_found` - Filen hittades inte

## 🛣️ Roadmap

- [ ] Stöd för Gradle-projekt auto-discovery
- [ ] Fler regler för app links verifiering  
- [ ] Konfigurationsfil för anpassade regler
- [ ] target SDK-version kontroller
- [ ] Utökad permission-analys
- [ ] VS Code extension
- [ ] IntelliJ plugin

## 📄 Licens

Proprietary License - Gracestack AB

## 🤝 Bidrag

Välkommen med issues och pull requests!

---

*Byggd med ❤️ av [Gracestack AB](https://gracestack.se)*
