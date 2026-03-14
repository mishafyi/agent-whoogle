#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "httpx[http2]>=0.28",
#   "beautifulsoup4>=4.13",
#   "cachetools>=5.0",
# ]
# ///
"""Agent Whoogle — local Google search for AI agents.

Extracted from Whoogle Search (https://github.com/benbusby/whoogle-search).
MIT License. Attribution: Ben Busby and the Whoogle project.

Usage: python search.py [OPTIONS] QUERY
"""

import argparse
import json
import os
import sys
from typing import Optional

# Python version check
if sys.version_info < (3, 9):
    print(json.dumps({
        "query": "",
        "results": [],
        "error": "requires_python_3.9",
        "message": "Python 3.9+ required",
    }))
    sys.exit(1)

# Add lib/ to path for whoogle_lite imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from whoogle_lite.request import WhoogleRequest, build_query
from whoogle_lite.parser import parse_results, has_captcha


def _output(query: str, results: list, error: Optional[str] = None, message: Optional[str] = None) -> dict:
    return {
        "query": query,
        "results": results,
        "error": error,
        "message": message,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Agent Whoogle — local Google search for AI agents",
        prog="search.py",
    )
    parser.add_argument("query", nargs="?", help="Search query string")
    parser.add_argument("--num", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("--start", type=int, default=0, help="Result offset for pagination")
    parser.add_argument("--lang", default="", help='Search language, e.g. "lang_en"')
    parser.add_argument("--country", default="", help='Country code, e.g. "US"')
    parser.add_argument("--safe", action="store_true", help="Enable SafeSearch")
    parser.add_argument("--proxy", default=None, help='Proxy URL, e.g. "socks5://127.0.0.1:9050"')
    parser.add_argument("--time", default="", dest="time_range", help="Time filter: hour, day, week, month, year")
    parser.add_argument("--json", action="store_true", default=True, help="Output as JSON (default)")
    parser.add_argument("--raw", action="store_true", help="Output as plain text")

    args = parser.parse_args()

    if not args.query:
        print(json.dumps(_output("", [], error="missing_query", message="No query provided. Usage: search.py QUERY")))
        sys.exit(1)

    try:
        # Build query string
        query_str = build_query(
            args.query,
            lang=args.lang,
            country=args.country,
            safe=args.safe,
            time_range=args.time_range,
            start=args.start,
            num=args.num,
        )

        # Build request and send
        import httpx

        req = WhoogleRequest(proxy=args.proxy)
        try:
            response = req.send(query=query_str)
        except (httpx.HTTPError, ConnectionError, TimeoutError, OSError) as e:
            print(json.dumps(_output(
                args.query, [],
                error="network_error",
                message=f"Failed to connect to Google: {str(e)}",
            )))
            print(f"Network error: {e}", file=sys.stderr)
            sys.exit(1)

        # Check for HTTP 429 or 403 (rate limiting / bot detection)
        if response.status_code in (403, 429):
            print(json.dumps(_output(
                args.query, [],
                error="rate_limited",
                message=f"Google returned HTTP {response.status_code}. Try again or use a proxy.",
            )))
            sys.exit(2)

        html = response.text

        # Check for CAPTCHA
        if has_captcha(html):
            print(json.dumps(_output(
                args.query, [],
                error="rate_limited",
                message="Google returned a CAPTCHA. Try again later or use a proxy.",
            )))
            sys.exit(2)

        # Parse results
        results = parse_results(html, num=args.num)

        if args.raw:
            if not results:
                print("No results found.", file=sys.stderr)
            else:
                for r in results:
                    print(f"{r['title']}")
                    print(f"  {r['url']}")
                    if r['snippet']:
                        print(f"  {r['snippet']}")
                    print()
            sys.exit(0)

        if not results:
            print(json.dumps(_output(args.query, [], message="No results found.")))
        else:
            print(json.dumps(_output(args.query, results)))

    except Exception as e:
        # Unexpected error (parsing bug, etc.) — report with full traceback
        print(json.dumps(_output(
            args.query, [],
            error="unexpected_error",
            message=f"Unexpected error: {str(e)}",
        )))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
