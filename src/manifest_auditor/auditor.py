from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Any

from .models import AuditReport, Finding, Severity

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
TOOL_NS = "{http://schemas.android.com/tools}"

VIEW_ACTION = "android.intent.action.VIEW"
DEFAULT_CATEGORY = "android.intent.category.DEFAULT"
BROWSABLE_CATEGORY = "android.intent.category.BROWSABLE"

DANGEROUS_PERMISSION_HINTS = {
    "android.permission.CAMERA": "camera",
    "android.permission.RECORD_AUDIO": "microphone",
    "android.permission.ACCESS_FINE_LOCATION": "location",
    "android.permission.ACCESS_COARSE_LOCATION": "location",
    "android.permission.ACCESS_BACKGROUND_LOCATION": "background location",
    "android.permission.READ_CONTACTS": "contacts",
    "android.permission.WRITE_CONTACTS": "contacts",
    "android.permission.READ_SMS": "sms",
    "android.permission.SEND_SMS": "sms",
    "android.permission.RECEIVE_SMS": "sms",
    "android.permission.READ_CALENDAR": "calendar",
    "android.permission.WRITE_CALENDAR": "calendar",
    "android.permission.READ_CALL_LOG": "call log",
    "android.permission.WRITE_CALL_LOG": "call log",
    "android.permission.READ_PHONE_STATE": "phone state",
    "android.permission.READ_PHONE_NUMBERS": "phone numbers",
    "android.permission.CALL_PHONE": "phone calls",
    "android.permission.ANSWER_PHONE_CALLS": "phone calls",
    "android.permission.READ_EXTERNAL_STORAGE": "external storage",
    "android.permission.WRITE_EXTERNAL_STORAGE": "external storage",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "all files",
    "android.permission.BODY_SENSORS": "body sensors",
    "android.permission.ACTIVITY_RECOGNITION": "physical activity",
    "android.permission.REQUEST_INSTALL_PACKAGES": "app installation",
    "android.permission.PACKAGE_USAGE_STATS": "app usage statistics",
    "android.permission.GET_ACCOUNTS": "accounts",
    "android.permission.USE_BIOMETRIC": "biometric authentication",
    "android.permission.USE_FINGERPRINT": "fingerprint authentication",
    "android.permission.NEARBY_WIFI_DEVICES": "nearby WiFi devices",
    "android.permission.BLUETOOTH_SCAN": "Bluetooth scanning",
    "android.permission.BLUETOOTH_CONNECT": "Bluetooth connections",
    "android.permission.UWB_RANGING": "ultra-wideband ranging",
}


def load_config(config_path: str) -> dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        import yaml
    except ImportError:
        # If PyYAML is not installed, return default config
        return {}
    
    config_file = Path(config_path)
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        import sys
        print(f"Warning: Could not load config file {config_path}: {e}", file=sys.stderr)
        return {}


def discover_manifests(project_root: Path, config: dict[str, Any] | None = None) -> list[str]:
    """Auto-discover AndroidManifest.xml files in an Android project."""
    manifests = []
    
    # Standard Android project structure
    standard_paths = [
        "app/src/main/AndroidManifest.xml",
        "app/src/debug/AndroidManifest.xml",
        "app/src/profile/AndroidManifest.xml",
        "src/main/AndroidManifest.xml",
        "src/debug/AndroidManifest.xml",
    ]
    
    for path in standard_paths:
        full_path = project_root / path
        if full_path.exists():
            manifests.append(str(full_path))
    
    # Search for any AndroidManifest.xml files recursively
    if not manifests:
        ignore_paths = config.get("ignore_paths", []) if config else []
        for manifest_file in project_root.rglob("AndroidManifest.xml"):
            # Skip files in build directories and custom ignore paths
            if "build/" not in str(manifest_file) and not any(
                ignore_path in str(manifest_file) for ignore_path in ignore_paths
            ):
                manifests.append(str(manifest_file))
    
    return sorted(list(set(manifests)))  # Remove duplicates and sort


def audit_manifests(manifest_paths: Iterable[str], config: dict[str, Any] | None = None) -> AuditReport:
    paths = [str(Path(path)) for path in manifest_paths]
    report = AuditReport(manifests=paths)

    for manifest_path in paths:
        report.findings.extend(_audit_single_manifest(Path(manifest_path), config))

    return report


def _audit_single_manifest(manifest_path: Path, config: dict[str, Any] | None = None) -> list[Finding]:
    findings: list[Finding] = []

    if not manifest_path.exists():
        return [
            Finding(
                severity=Severity.ERROR,
                rule_id="file.not_found",
                message="Manifestfilen hittades inte.",
                file_path=str(manifest_path),
            )
        ]

    try:
        tree = ET.parse(manifest_path)
    except ET.ParseError as exc:
        return [
            Finding(
                severity=Severity.ERROR,
                rule_id="manifest.parse_error",
                message=f"Kunde inte läsa manifestet: {exc}",
                file_path=str(manifest_path),
            )
        ]

    root = tree.getroot()
    package_name = root.attrib.get("package", "")
    application = root.find("application")

    if application is None:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                rule_id="manifest.missing_application",
                message="Manifestet saknar <application>-element.",
                file_path=str(manifest_path),
            )
        )
        return findings

    findings.extend(_audit_exported_components(application, manifest_path, config))
    findings.extend(_audit_intent_filters(application, manifest_path, package_name, config))
    findings.extend(_audit_permissions(root, manifest_path, config))
    findings.extend(_audit_sdk_versions(root, manifest_path, config))

    return findings


def _get_rule_severity(rule_id: str, default_severity: Severity, config: dict[str, Any] | None = None) -> Severity:
    """Get severity for a rule from config, with fallback to default."""
    if not config:
        return default_severity
    
    rules_config = config.get("rules", {})
    severity_str = rules_config.get(rule_id, default_severity.value)
    
    if severity_str == "disabled":
        return None  # Rule is disabled
    elif severity_str == "error":
        return Severity.ERROR
    elif severity_str == "warning":
        return Severity.WARNING
    elif severity_str == "info":
        return Severity.INFO
    else:
        return default_severity


def _audit_exported_components(application: ET.Element, manifest_path: Path, config: dict[str, Any] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    component_tags = ("activity", "activity-alias", "service", "receiver", "provider")

    for component in application:
        if _local_name(component.tag) not in component_tags:
            continue

        intent_filters = [child for child in component if _local_name(child.tag) == "intent-filter"]
        exported_attr = component.attrib.get(f"{ANDROID_NS}exported")
        component_name = component.attrib.get(f"{ANDROID_NS}name")

        if intent_filters and exported_attr is None:
            severity = _get_rule_severity("component.missing_exported", Severity.ERROR, config)
            if severity:
                findings.append(
                    Finding(
                        severity=severity,
                        rule_id="component.missing_exported",
                        message=(
                            "Komponenten har intent-filter men saknar android:exported. "
                            "Detta blir ett byggfel eller en risk beroende på targetSdk."
                        ),
                        file_path=str(manifest_path),
                        element=_local_name(component.tag),
                        component_name=component_name,
                    )
                )

    return findings


def _audit_intent_filters(application: ET.Element, manifest_path: Path, package_name: str, config: dict[str, Any] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    deeplink_configs = []  # Track for duplicate detection

    for component in application:
        component_tag = _local_name(component.tag)
        if component_tag not in {"activity", "activity-alias", "service", "receiver"}:
            continue

        component_name = component.attrib.get(f"{ANDROID_NS}name")
        for intent_filter in [child for child in component if _local_name(child.tag) == "intent-filter"]:
            actions = [
                child.attrib.get(f"{ANDROID_NS}name", "")
                for child in intent_filter
                if _local_name(child.tag) == "action"
            ]
            categories = {
                child.attrib.get(f"{ANDROID_NS}name", "")
                for child in intent_filter
                if _local_name(child.tag) == "category"
            }
            data_elems = [child for child in intent_filter if _local_name(child.tag) == "data"]
            auto_verify = intent_filter.attrib.get(f"{ANDROID_NS}autoVerify")

            if VIEW_ACTION in actions and data_elems:
                if DEFAULT_CATEGORY not in categories:
                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_id="deeplink.missing_default_category",
                            message="Deep link-intent filter saknar DEFAULT-kategorin.",
                            file_path=str(manifest_path),
                            element="intent-filter",
                            component_name=component_name,
                        )
                    )
                if BROWSABLE_CATEGORY not in categories:
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            rule_id="deeplink.missing_browsable_category",
                            message="Deep link-intent filter saknar BROWSABLE-kategorin.",
                            file_path=str(manifest_path),
                            element="intent-filter",
                            component_name=component_name,
                        )
                    )

                for data in data_elems:
                    scheme = data.attrib.get(f"{ANDROID_NS}scheme")
                    host = data.attrib.get(f"{ANDROID_NS}host")
                    path_prefix = data.attrib.get(f"{ANDROID_NS}pathPrefix")
                    path_pattern = data.attrib.get(f"{ANDROID_NS}pathPattern")
                    path = data.attrib.get(f"{ANDROID_NS}path")
                    
                    if not scheme:
                        findings.append(
                            Finding(
                                severity=Severity.ERROR,
                                rule_id="deeplink.missing_scheme",
                                message="Intent-filter har <data> men saknar android:scheme.",
                                file_path=str(manifest_path),
                                element="data",
                                component_name=component_name,
                            )
                        )
                    
                    # Check for missing path specification for HTTP/HTTPS
                    if scheme in {"http", "https"} and host and not any([path_prefix, path_pattern, path]):
                        findings.append(
                            Finding(
                                severity=Severity.WARNING,
                                rule_id="deeplink.missing_path_specification",
                                message="HTTP/HTTPS deep link saknar path-specifikation (pathPrefix/pathPattern/path).",
                                file_path=str(manifest_path),
                                element="data",
                                component_name=component_name,
                                details={"scheme": scheme, "host": host},
                            )
                        )
                    
                    # Check for invalid characters in host
                    if host and any(char in host for char in [' ', '\t', '\n', '\r']):
                        findings.append(
                            Finding(
                                severity=Severity.ERROR,
                                rule_id="deeplink.invalid_host_characters",
                                message="Host innehåller ogiltiga tecken (whitespace).",
                                file_path=str(manifest_path),
                                element="data",
                                component_name=component_name,
                                details={"scheme": scheme, "host": host},
                            )
                        )
                    
                    # Track for duplicate detection
                    if scheme and host:
                        deeplink_configs.append({
                            "scheme": scheme,
                            "host": host,
                            "component": component_name,
                            "file_path": str(manifest_path)
                        })
                    
                    if scheme in {"http", "https"} and auto_verify != "true":
                        findings.append(
                            Finding(
                                severity=Severity.WARNING,
                                rule_id="deeplink.http_without_autoverify",
                                message=(
                                    "HTTP/HTTPS deep link saknar autoVerify=\"true\". "
                                    "App Links kan vara ofullständigt konfigurerat."
                                ),
                                file_path=str(manifest_path),
                                element="intent-filter",
                                component_name=component_name,
                                details={"scheme": scheme, "host": host or ""},
                            )
                        )

    # Check for duplicate deeplink configurations
    host_scheme_counts = {}
    for config in deeplink_configs:
        key = (config["scheme"], config["host"])
        host_scheme_counts[key] = host_scheme_counts.get(key, 0) + 1
    
    for (scheme, host), count in host_scheme_counts.items():
        if count > 1:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_id="deeplink.duplicate_host_scheme",
                    message=f"Flera komponenter hanterar samma deeplink ({scheme}://{host}). Detta kan orsaka konflikter.",
                    file_path=str(manifest_path),
                    element="intent-filter",
                    details={"scheme": scheme, "host": host, "count": count},
                )
            )

    if package_name and not package_name.strip():
        findings.append(
            Finding(
                severity=Severity.INFO,
                rule_id="manifest.empty_package",
                message="Manifestet har ett tomt package-attribut.",
                file_path=str(manifest_path),
            )
        )

    return findings


def _audit_permissions(root: ET.Element, manifest_path: Path, config: dict[str, Any] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    permissions = [
        perm.attrib.get(f"{ANDROID_NS}name", "")
        for perm in root.findall("uses-permission")
    ]

    for permission in permissions:
        if permission in DANGEROUS_PERMISSION_HINTS:
            target = DANGEROUS_PERMISSION_HINTS[permission]
            findings.append(
                Finding(
                    severity=Severity.INFO,
                    rule_id="permission.rationale_hint",
                    message=(
                        f"Manifestet begär {permission}. Kontrollera att appen visar en tydlig "
                        f"rational för {target}-åtkomst innan runtime-begäran."
                    ),
                    file_path=str(manifest_path),
                    element="uses-permission",
                    details={"permission": permission, "ux_hint": target},
                )
            )

    if "android.permission.INTERNET" in permissions:
        findings.append(
            Finding(
                severity=Severity.INFO,
                rule_id="permission.internet_note",
                message="INTERNET kräver ingen runtime-dialog men bör fortfarande motiveras i appens säkerhetsmodell.",
                file_path=str(manifest_path),
                element="uses-permission",
                details={"permission": "android.permission.INTERNET"},
            )
        )

    return findings


def _audit_sdk_versions(root: ET.Element, manifest_path: Path, config: dict[str, Any] | None = None) -> list[Finding]:
    """Audit target SDK version and compatibility settings."""
    findings: list[Finding] = []
    
    # Check uses-sdk elements
    uses_sdk = root.find("uses-sdk")
    if uses_sdk is not None:
        target_sdk = uses_sdk.attrib.get(f"{ANDROID_NS}targetSdkVersion")
        min_sdk = uses_sdk.attrib.get(f"{ANDROID_NS}minSdkVersion")
        compile_sdk = uses_sdk.attrib.get(f"{ANDROID_NS}compileSdkVersion")
        
        # Target SDK version checks
        if target_sdk:
            try:
                target_version = int(target_sdk)
                
                # Warn about outdated target SDK
                if target_version < 33:  # Android 13
                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_id="sdk.outdated_target_sdk",
                            message=(
                                f"targetSdkVersion {target_version} är lägre än 33 (Android 13). "
                                "Google Play kräver ofta uppdatering för nya appar."
                            ),
                            file_path=str(manifest_path),
                            element="uses-sdk",
                            details={"target_sdk": target_version, "recommended": 34},
                        )
                    )
                
                # Error for very old target SDK
                if target_version < 30:  # Android 11
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            rule_id="sdk.very_old_target_sdk",
                            message=(
                                f"targetSdkVersion {target_version} är mycket gammal (före Android 11). "
                                "Många moderna API:er och säkerhetsfunktioner saknas."
                            ),
                            file_path=str(manifest_path),
                            element="uses-sdk",
                            details={"target_sdk": target_version, "minimum_recommended": 30},
                        )
                    )
                
            except ValueError:
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_id="sdk.invalid_target_sdk_format",
                        message=f"targetSdkVersion '{target_sdk}' är inte ett giltigt heltal.",
                        file_path=str(manifest_path),
                        element="uses-sdk",
                        details={"target_sdk": target_sdk},
                    )
                )
        else:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id="sdk.missing_target_sdk",
                    message="targetSdkVersion saknas. Detta rekommenderas starkt för alla appar.",
                    file_path=str(manifest_path),
                    element="uses-sdk",
                )
            )
        
        # Min SDK version checks
        if min_sdk:
            try:
                min_version = int(min_sdk)
                
                # Warn about very high min SDK
                if min_version > 26:  # Android 8.0
                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_id="sdk.high_min_sdk",
                            message=(
                                f"minSdkVersion {min_version} är hög. "
                                f"Appen kommer inte att fungera på {min_version-1}+ enheter."
                            ),
                            file_path=str(manifest_path),
                            element="uses-sdk",
                            details={"min_sdk": min_version},
                        )
                    )
                
                # Info about low min SDK implications
                if min_version < 21:  # Android 5.0
                    findings.append(
                        Finding(
                            severity=Severity.INFO,
                            rule_id="sdk.low_min_sdk_implications",
                            message=(
                                f"minSdkVersion {min_version} kräver bakåtkompatibilitetstestning. "
                                "Kontrollera runtime permissions och modern material design."
                            ),
                            file_path=str(manifest_path),
                            element="uses-sdk",
                            details={"min_sdk": min_version},
                        )
                    )
                    
            except ValueError:
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_id="sdk.invalid_min_sdk_format",
                        message=f"minSdkVersion '{min_sdk}' är inte ett giltigt heltal.",
                        file_path=str(manifest_path),
                        element="uses-sdk",
                        details={"min_sdk": min_sdk},
                    )
                )
        
        # Check for reasonable version gaps
        if target_sdk and min_sdk:
            try:
                target_version = int(target_sdk)
                min_version = int(min_sdk)
                
                if target_version - min_version > 10:
                    findings.append(
                        Finding(
                            severity=Severity.INFO,
                            rule_id="sdk.large_version_gap",
                            message=(
                                f"Stor skillnad mellan targetSdkVersion ({target_version}) "
                                f"och minSdkVersion ({min_version}). "
                                "Se över om du kan höra minSdkVersion."
                            ),
                            file_path=str(manifest_path),
                            element="uses-sdk",
                            details={"target_sdk": target_version, "min_sdk": min_version},
                        )
                    )
            except ValueError:
                pass  # Already handled above
    else:
        findings.append(
            Finding(
                severity=Severity.WARNING,
                rule_id="sdk.missing_uses_sdk",
                message="<uses-sdk>-element saknas. Rekommenderas för att specificera SDK-versioner.",
                file_path=str(manifest_path),
                element="manifest",
            )
        )
    
    return findings


def format_human_report(report: AuditReport) -> str:
    lines = []
    lines.append("Android Manifest Audit")
    lines.append("=" * 24)
    lines.append(f"Manifestfiler: {len(report.manifests)}")
    lines.append(f"Fel: {report.errors} | Varningar: {report.warnings} | Info: {report.info}")
    lines.append("")

    if not report.findings:
        lines.append("Inga fynd. Manifestet ser bra ut för de regler som verktyget kontrollerar.")
        return "\n".join(lines)

    for finding in report.findings:
        icon = {Severity.ERROR: "✗", Severity.WARNING: "!", Severity.INFO: "i"}[finding.severity]
        lines.append(f"{icon} [{finding.severity.value.upper()}] {finding.rule_id}")
        lines.append(f"  Fil: {finding.file_path}")
        if finding.element:
            lines.append(f"  Element: {finding.element}")
        if finding.component_name:
            lines.append(f"  Komponent: {finding.component_name}")
        lines.append(f"  {finding.message}")
        if finding.details:
            lines.append(f"  Detaljer: {json.dumps(finding.details, ensure_ascii=False)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def report_to_json(report: AuditReport) -> str:
    return json.dumps(
        {
            "manifests": report.manifests,
            "summary": {
                "errors": report.errors,
                "warnings": report.warnings,
                "info": report.info,
                "total": len(report.findings),
            },
            "findings": [
                {
                    **asdict(finding),
                    "severity": finding.severity.value,
                }
                for finding in report.findings
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def report_to_sarif(report: AuditReport) -> str:
    """Convert audit report to SARIF format for GitHub integration."""
    import uuid
    from datetime import datetime, timezone
    
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "android-manifest-auditor",
                        "version": "0.1.0",
                        "informationUri": "https://github.com/gracestack/android-manifest-auditor",
                        "rules": [
                            {
                                "id": finding.rule_id,
                                "name": finding.rule_id.replace(".", "_"),
                                "shortDescription": {
                                    "text": finding.message
                                },
                                "fullDescription": {
                                    "text": finding.message
                                },
                                "defaultConfiguration": {
                                    "level": {
                                        Severity.ERROR: "error",
                                        Severity.WARNING: "warning", 
                                        Severity.INFO: "note"
                                    }[finding.severity]
                                },
                                "helpUri": f"https://github.com/gracestack/android-manifest-auditor/blob/main/docs/rules.md#{finding.rule_id}"
                            }
                            for finding in report.findings
                        ]
                    }
                },
                "results": [
                    {
                        "ruleId": finding.rule_id,
                        "level": {
                            Severity.ERROR: "error",
                            Severity.WARNING: "warning",
                            Severity.INFO: "note"
                        }[finding.severity],
                        "message": {
                            "text": finding.message
                        },
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {
                                        "uri": finding.file_path
                                    },
                                    "region": {
                                        "startLine": 1,
                                        "startColumn": 1,
                                        "endLine": 1,
                                        "endColumn": 1
                                    }
                                },
                                "logicalLocations": [
                                    {
                                        "fullyQualifiedName": finding.component_name or "unknown",
                                        "kind": finding.element or "manifest"
                                    }
                                ] if finding.component_name or finding.element else []
                            }
                        ],
                        "properties": finding.details if finding.details else {}
                    }
                    for finding in report.findings
                ]
            }
        ]
    }
    
    return json.dumps(sarif, ensure_ascii=False, indent=2)


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
