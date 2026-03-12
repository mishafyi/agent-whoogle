import json
import subprocess
import sys
import os

SEARCH_SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'search.py')


def test_cli_no_query():
    """Running without a query should exit with error."""
    result = subprocess.run(
        [sys.executable, SEARCH_SCRIPT],
        capture_output=True, text=True
    )
    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["error"] is not None


def test_cli_help():
    result = subprocess.run(
        [sys.executable, SEARCH_SCRIPT, '--help'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert 'query' in result.stdout.lower()


def test_cli_output_format():
    """Test that output is valid JSON with expected schema.
    Uses a bad proxy to trigger a network error (which still produces valid JSON).
    """
    result = subprocess.run(
        [sys.executable, SEARCH_SCRIPT, '--proxy', 'http://invalid:0', 'test query'],
        capture_output=True, text=True,
        timeout=30
    )
    output = json.loads(result.stdout)
    assert "query" in output
    assert "results" in output
    assert "error" in output
    assert "message" in output
    assert output["query"] == "test query"
