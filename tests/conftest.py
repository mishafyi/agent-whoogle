import sys
import os

# Add lib/ to path so all tests can import whoogle_lite
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import pytest


@pytest.fixture(autouse=True)
def cleanup_clients():
    """Clean up HTTP client cache after each test (lazy import for early tasks)."""
    yield
    try:
        from whoogle_lite.provider import close_all_clients
        close_all_clients()
    except ImportError:
        pass  # provider.py not created yet in early tasks
    except Exception:
        pass
