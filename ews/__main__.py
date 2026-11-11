"""CLI entrypoint for local smoke checks."""

from __future__ import annotations

import argparse
import platform
import sys

from ews import __version__


def cmd_status() -> int:
    print(f"ews version={__version__}")
    print(f"python={sys.version.split()[0]}")
    print(f"platform={platform.platform()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ews")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Print environment status")
    args = parser.parse_args(argv)
    if args.command == "status":
        return cmd_status()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
