from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from manifest_auditor.auditor import audit_manifests, discover_manifests
from manifest_auditor.models import Severity


class TestAuditor:
    def test_missing_exported_attribute(self):
        """Test that components with intent filters but no exported attribute are flagged."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <application android:label="Test">
        <activity android:name=".MainActivity">
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="https" android:host="example.com" />
            </intent-filter>
        </activity>
    </application>
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            report = audit_manifests([f.name])
            
            # Should find missing exported attribute
            exported_errors = [
                f for f in report.findings 
                if f.rule_id == "component.missing_exported"
            ]
            assert len(exported_errors) == 1
            assert exported_errors[0].severity == Severity.ERROR
            
            Path(f.name).unlink()

    def test_deeplink_missing_browsable_category(self):
        """Test that deep links without BROWSABLE category are flagged."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <application android:label="Test">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:scheme="https" android:host="example.com" />
            </intent-filter>
        </activity>
    </application>
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            report = audit_manifests([f.name])
            
            # Should find missing BROWSABLE category
            browsable_errors = [
                f for f in report.findings 
                if f.rule_id == "deeplink.missing_browsable_category"
            ]
            assert len(browsable_errors) == 1
            assert browsable_errors[0].severity == Severity.ERROR
            
            Path(f.name).unlink()

    def test_deeplink_duplicate_host_scheme(self):
        """Test that duplicate deep link configurations are flagged."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <application android:label="Test">
        <activity android:name=".Activity1" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="https" android:host="duplicate.com" />
            </intent-filter>
        </activity>
        <activity android:name=".Activity2" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="https" android:host="duplicate.com" />
            </intent-filter>
        </activity>
    </application>
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            report = audit_manifests([f.name])
            
            # Should find duplicate host/scheme
            duplicate_warnings = [
                f for f in report.findings 
                if f.rule_id == "deeplink.duplicate_host_scheme"
            ]
            assert len(duplicate_warnings) == 1
            assert duplicate_warnings[0].severity == Severity.WARNING
            assert duplicate_warnings[0].details["count"] == 2
            
            Path(f.name).unlink()

    def test_permission_rationale_hints(self):
        """Test that dangerous permissions generate rationale hints."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <application android:label="Test" />
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            report = audit_manifests([f.name])
            
            # Should find rationale hints for both permissions
            rationale_hints = [
                f for f in report.findings 
                if f.rule_id == "permission.rationale_hint"
            ]
            assert len(rationale_hints) == 2
            assert all(f.severity == Severity.INFO for f in rationale_hints)
            
            # Check specific permissions
            permissions_found = {f.details["permission"] for f in rationale_hints}
            expected_permissions = {
                "android.permission.CAMERA",
                "android.permission.ACCESS_FINE_LOCATION"
            }
            assert permissions_found == expected_permissions
            
            Path(f.name).unlink()

    def test_valid_manifest_no_errors(self):
        """Test that a valid manifest produces no errors."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <uses-sdk android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:label="Test">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter android:autoVerify="true">
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="https" android:host="example.com" android:pathPrefix="/docs" />
            </intent-filter>
        </activity>
    </application>
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            report = audit_manifests([f.name])
            
            # Should have no errors, only info messages
            assert report.errors == 0
            assert report.warnings == 0
            assert report.info >= 0  # May have info messages
            
            Path(f.name).unlink()


class TestDiscovery:
    def test_discover_manifests_standard_structure(self):
        """Test manifest discovery in standard Android project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create standard Android structure
            app_main = tmppath / "app" / "src" / "main"
            app_main.mkdir(parents=True)
            manifest_file = app_main / "AndroidManifest.xml"
            manifest_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<manifest package="com.example.test" />""")
            
            discovered = discover_manifests(tmppath)
            assert len(discovered) == 1
            assert discovered[0].endswith("app/src/main/AndroidManifest.xml")

    def test_discover_manifests_recursive_fallback(self):
        """Test recursive manifest discovery when standard paths don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create manifest in non-standard location
            custom_dir = tmppath / "custom" / "path"
            custom_dir.mkdir(parents=True)
            manifest_file = custom_dir / "AndroidManifest.xml"
            manifest_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<manifest package="com.example.test" />""")
            
            discovered = discover_manifests(tmppath)
            assert len(discovered) == 1
            assert discovered[0].endswith("custom/path/AndroidManifest.xml")

    def test_discover_manifests_ignores_build_dirs(self):
        """Test that build directories are ignored during discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create manifest in build directory (should be ignored)
            build_dir = tmppath / "build" / "intermediates"
            build_dir.mkdir(parents=True)
            build_manifest = build_dir / "AndroidManifest.xml"
            build_manifest.write_text("""<?xml version="1.0" encoding="utf-8"?>
<manifest package="com.example.test" />""")
            
            # Create manifest in normal location (should be found)
            normal_dir = tmppath / "src" / "main"
            normal_dir.mkdir(parents=True)
            normal_manifest = normal_dir / "AndroidManifest.xml"
            normal_manifest.write_text("""<?xml version="1.0" encoding="utf-8"?>
<manifest package="com.example.test" />""")
            
            discovered = discover_manifests(tmppath)
            assert len(discovered) == 1
            assert "build/" not in discovered[0]
