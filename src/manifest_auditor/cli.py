from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .auditor import audit_manifests, format_human_report, report_to_json, report_to_sarif, discover_manifests, load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manifest-audit",
        description="Audit AndroidManifest.xml for common deep link, export and permission issues.",
    )
    parser.add_argument(
        "manifests",
        nargs="*",
        help="One or more AndroidManifest.xml files to audit. If omitted, will auto-discover manifests.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the audit result as JSON.",
    )
    parser.add_argument(
        "--sarif",
        action="store_true",
        help="Print the audit result as SARIF for GitHub integration.",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (YAML). Default: manifest-audit-config.yaml",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate output format options
    if args.json and args.sarif:
        print("Error: Cannot use both --json and --sarif options.", file=sys.stderr)
        return 1

    # Load configuration
    config_path = args.config or "manifest-audit-config.yaml"
    config = load_config(config_path) if Path(config_path).exists() else None

    # Auto-discover manifests if none provided
    if not args.manifests:
        discovered = discover_manifests(Path.cwd(), config)
        if not discovered:
            print("Inga manifestfiler hittades. Ange sökväg manuellt.", file=sys.stderr)
            return 1
        args.manifests = discovered

    report = audit_manifests(args.manifests, config)

    if args.sarif:
        print(report_to_sarif(report))
    elif args.json:
        print(report_to_json(report))
    else:
        print(format_human_report(report), end="")

    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
