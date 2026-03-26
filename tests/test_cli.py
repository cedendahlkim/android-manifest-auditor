from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from manifest_auditor.cli import main


class TestCLI:
    def test_cli_with_valid_manifest(self):
        """Test CLI with a valid manifest file."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <application android:label="Test">
        <activity android:name=".MainActivity" android:exported="true" />
    </application>
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            # Test normal output
            result = main([f.name])
            assert result == 0  # No errors
            
            Path(f.name).unlink()

    def test_cli_with_invalid_manifest(self):
        """Test CLI with manifest that has errors."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <application android:label="Test">
        <activity android:name=".MainActivity">
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <data android:scheme="https" android:host="example.com" />
            </intent-filter>
        </activity>
    </application>
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            # Should return error code due to missing exported and BROWSABLE
            result = main([f.name])
            assert result == 1  # Has errors
            
            Path(f.name).unlink()

    def test_cli_json_output(self, capsys):
        """Test JSON output format."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <uses-permission android:name="android.permission.CAMERA" />
    <application android:label="Test" />
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            main([f.name, "--json"])
            captured = capsys.readouterr()
            
            # Should be valid JSON
            data = json.loads(captured.out)
            assert "manifests" in data
            assert "summary" in data
            assert "findings" in data
            
            Path(f.name).unlink()

    def test_cli_sarif_output(self, capsys):
        """Test SARIF output format."""
        manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <uses-permission android:name="android.permission.CAMERA" />
    <application android:label="Test" />
</manifest>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(manifest_content)
            f.flush()
            
            main([f.name, "--sarif"])
            captured = capsys.readouterr()
            
            # Should be valid SARIF
            data = json.loads(captured.out)
            assert "$schema" in data
            assert "version" in data
            assert "runs" in data
            assert data["version"] == "2.1.0"
            
            Path(f.name).unlink()

    def test_cli_conflicting_output_options(self, capsys):
        """Test that conflicting output options are rejected."""
        result = main(["--json", "--sarif"])
        assert result == 1
        
        captured = capsys.readouterr()
        assert "Cannot use both --json and --sarif" in captured.err

    def test_cli_nonexistent_file(self):
        """Test CLI with non-existent file."""
        result = main(["/nonexistent/file.xml"])
        assert result == 1  # Should error

    def test_cli_auto_discovery(self, monkeypatch):
        """Test auto-discovery when no files are specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create a valid manifest file
            manifest_file = tmppath / "AndroidManifest.xml"
            manifest_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test">
    <application android:label="Test" />
</manifest>""")
            
            # Change to temp directory
            monkeypatch.chdir(tmppath)
            
            # Test auto-discovery (no arguments)
            result = main([])
            assert result == 0  # Should find and process the manifest
