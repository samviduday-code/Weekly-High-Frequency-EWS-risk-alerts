"""CLI entrypoint for HF EWS tooling."""

from __future__ import annotations

import argparse
import platform
import sys

from ews import __version__
from ews.weekly import run_weekly


def cmd_status() -> int:
    print(f"ews version={__version__}")
    print(f"python={sys.version.split()[0]}")
    print(f"platform={platform.platform()}")
    return 0


def _run_weekly_and_report(*, post_email: bool, skip_fetch: bool) -> int:
    result = run_weekly(post_email=post_email, skip_fetch=skip_fetch)
    if result.reason != "ok" or result.exit_code != 0:
        if result.message:
            print(result.message, file=sys.stderr)
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="ews")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Print environment status")
    weekly = sub.add_parser("weekly", help="Run Monday HF EWS digest pipeline")
    weekly.add_argument(
        "--post-email",
        action="store_true",
        help="Email the digest to samvid.uday@navi.com (override with EWS_EMAIL_TO)",
    )
    weekly.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip fetch_new_hf_and_sep_actuals.py (build only)",
    )

    args = parser.parse_args(argv)
    if args.command == "status":
        return cmd_status()
    if args.command == "weekly":
        return _run_weekly_and_report(
            post_email=args.post_email,
            skip_fetch=args.skip_fetch,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
