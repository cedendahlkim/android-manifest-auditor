# 🤝 Bidra till Android Manifest Auditor

Vi älskar bidrag! Oavsett om du vill rapportera en bugg, föreslå en ny funktion eller bidra med kod, här är guiden för att komma igång.

## 📋 Innehåll

- [Rapportera Buggar](#rapportera-buggar)
- [Föreslå Funktionalitet](#föreslå-funktionalitet)
- [Utvecklingsguide](#utvecklingsguide)
- [Kodstandarder](#kodstandarder)
- [Pull Request Process](#pull-request-process)

## 🐛 Rapportera Buggar

Innan du skapar en issue, kontrollera:

1. **Sök befintliga issues** - Kanske har någon redan rapporterat det
2. **Kontrollera senaste versionen** - Uppgradera till senaste versionen
3. **Testa minimalt exempel** - Isolera problemet

### Skapa Bug Report

Använd vår bug report template:

```markdown
## 🐛 Bug Description
Kort beskrivning av problemet

## 📋 Steg att återskapa
1. Kör `manifest-audit path/to/AndroidManifest.xml`
2. Förväntat: X
3. Faktiskt: Y

## 🎯 Förväntat beteende
Beskriv vad du förväntade dig skulle hända

## 📱 Environment
- OS: [t.ex. Ubuntu 22.04]
- Python version: [t.ex. 3.11]
- Verktygsversion: [t.ex. 0.1.0]

## 📎 Exempel
Bifoga manifestfil som reproducerar problemet
```

## 💡 Föreslå Funktionalitet

Vi älskar idéer! Här är hur du föreslår nya funktioner:

### Feature Request Template

```markdown
## 🚀 Funktionsbeskrivning
Klar och koncis beskrivning av önskad funktion

## 🎯 Problem den löser
Vilket problem hjälper denna funktion att lösa?

## 💡 Förslag på lösning
Beskriv hur du tänker dig att funktionen ska implementeras

## 🔄 Alternativ
Har du övervägt andra lösningar?

## 📎 Exempel
Visa exempel på hur funktionen skulle användas
```

## 🛠️ Utvecklingsguide

### Förutsättningar

- Python 3.10+
- Git
- GitHub konto

### Lokal utveckling

```bash
# 1. Fork repository
# 2. Klona din fork
git clone https://github.com/DITT_NAMN/android-manifest-auditor.git
cd android-manifest-auditor

# 3. Skapa virtuell miljö
python -m venv venv
source venv/bin/activate  # Linux/Mac
# eller venv\Scripts\activate  # Windows

# 4. Installera med dev-dependencies
pip install -e ".[all]"

# 5. Kör tester
pytest

# 6. Skapa ny branch
git checkout -b feature/din-nya-funktion
```

### Projektstruktur

```
src/manifest_auditor/
├── __init__.py
├── cli.py          # CLI interface
├── auditor.py      # Core audit logic
└── models.py       # Data models

tests/
├── __init__.py
├── test_auditor.py # Core functionality tests
└── test_cli.py     # CLI tests

.github/workflows/
└── manifest-audit.yml  # CI/CD
```

## 📝 Kodstandarder

### Python Style
- **Type hints** obligatoriska
- **Docstrings** för alla publika funktioner
- **Maximum line length**: 88 tecken
- **Import ordning**: standard library → third party → local

### Exempel

```python
from __future__ import annotations

from typing import Iterable
from pathlib import Path

from .models import Finding, Severity


def audit_manifests(manifest_paths: Iterable[str]) -> list[Finding]:
    """Audit Android manifest files.
    
    Args:
        manifest_paths: Paths to AndroidManifest.xml files
        
    Returns:
        List of audit findings
    """
    # Implementation here
    pass
```

### Test-standarder

```python
def test_function_name_descriptive(self):
    """Test description explaining what is being tested."""
    # Arrange
    manifest_content = """<?xml version="1.0" encoding="utf-8"?>
    <manifest package="com.example.test" />"""
    
    # Act
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml') as f:
        f.write(manifest_content)
        result = audit_manifests([f.name])
    
    # Assert
    assert len(result.findings) == 0
```

## 🔄 Pull Request Process

### För PR

1. **Fork & Branch**: Skapa branch från `main`
2. **Testa**: Se till att alla tester passerar
3. **Documentation**: Uppdatera README om nödvändigt
4. **Commit**: Följ [Conventional Commits](https://www.conventionalcommits.org/)

### Commit Messages

```
feat: add SDK version validation
fix: handle missing application element
docs: update installation instructions
test: add tests for deep link validation
```

### PR Checklist

- [ ] Tester passerar
- [ ] Kod följer style guidelines
- [ ] Docstrings tillagda/uppdaterade
- [ ] README uppdaterad (om nödvändigt)
- [ ] CHANGELOG.md uppdaterad

### PR Template

```markdown
## 🎯 Ändringar
Beskriv vad denna PR ändrar

## 🧪 Testning
Hur har du testat dina ändringar?

## 📋 Checklist
- [ ] Kod följer projektets standarder
- [ ] Tester tillagda/uppdaterade
- [ ] Dokumentation uppdaterad

## 🔗 Relaterade Issues
Closes #123
```

## 🏆 Tack för ditt bidrag!

Alla bidrag är uppskattade! Vi kommer att:

- 🌟 **Acknowledge** alla bidrag i vår README
- 🏷️ **Tagga** contributors i releases
- 📧 **Contacta** för större bidrag

## 📞 Kontakt

- **Issues**: [GitHub Issues](https://github.com/gracestack/android-manifest-auditor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gracestack/android-manifest-auditor/discussions)
- **Email**: gracestackab@gmail.com

---

*Byggd med ❤️ av Gracestack AB community*
