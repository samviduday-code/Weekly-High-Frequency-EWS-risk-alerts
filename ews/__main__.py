"""CLI entrypoint for local smoke checks."""

from __future__ import annotations

import argparse
import platform
import sys

from ews import __version__
from ews.weekly import result_to_json, run_weekly


def cmd_status() -> int:
    print(f"ews version={__version__}")
    print(f"python={sys.version.split()[0]}")
    print(f"platform={platform.platform()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ews")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Print environment status")
    weekly_p = sub.add_parser("weekly", help="Run Monday HF EWS refresh and summary")
    weekly_p.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable result JSON to stdout",
    )
    args = parser.parse_args(argv)
    if args.command == "status":
        return cmd_status()
    if args.command == "weekly":
        result = run_weekly()
        if args.json:
            print(result_to_json(result))
        else:
            print(result.weekly_message)
            if result.major_message:
                print("\n---\n")
                print(result.major_message)
        return 0 if result.ok or result.weekly_message else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
