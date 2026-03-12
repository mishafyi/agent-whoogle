"""Request building for Google Search — headers, cookies, query construction.

Extracted from Whoogle Search (app/request.py). Removed: Tor integration,
Flask dependencies, Config class dependency. Kept: all anti-detection mechanisms.
"""

import os
import urllib.parse as urlparse
from typing import Dict, Optional, Tuple

from .ua_generator import load_ua_pool, get_random_ua, DEFAULT_FALLBACK_UA
from .provider import get_http_client


# Time range shortcuts
TIME_RANGES = {
    'hour': 'h', 'day': 'd', 'week': 'w', 'month': 'm', 'year': 'y',
    'h': 'h', 'd': 'd', 'w': 'w', 'm': 'm', 'y': 'y',
}

# Modern Chrome UA for image search (Google Images rejects legacy UAs)
IMAGE_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/127.0.0.0 Safari/537.36'
)


def build_query(
    query: str,
    lang: str = '',
    country: str = '',
    safe: bool = False,
    time_range: str = '',
    start: int = 0,
    num: int = 10,
) -> str:
    """Build the Google search query string."""
    encoded = urlparse.quote(query)
    parts = [encoded]

    if lang:
        parts.append(f'&lr={lang}')

    if country:
        parts.append(f'&gl={country}')

    parts.append(f'&safe={"active" if safe else "off"}')

    if time_range:
        code = TIME_RANGES.get(time_range.lower(), '')
        if code:
            parts.append(f'&tbs=qdr:{code}')

    if start > 0:
        parts.append(f'&start={start}')

    if num != 10:
        parts.append(f'&num={num}')

    return ''.join(parts)


class WhoogleRequest:
    """Builds and sends Google search requests with full anti-detection."""

    def __init__(self, proxy: Optional[str] = None):
        self.search_url = 'https://www.google.com/search?gbv=1&q='
        self.image_search_url = 'https://www.google.com/search?udm=2&q='

        # Set up proxy configuration
        self.proxies: Dict[str, str] = {}
        if proxy:
            self.proxies = {'https': proxy, 'http': proxy}
        else:
            proxy_path = os.environ.get('WHOOGLE_PROXY_LOC', '')
            if proxy_path:
                proxy_type = os.environ.get('WHOOGLE_PROXY_TYPE', '')
                proxy_user = os.environ.get('WHOOGLE_PROXY_USER', '')
                proxy_pass = os.environ.get('WHOOGLE_PROXY_PASS', '')
                auth_str = f'{proxy_user}:{proxy_pass}@' if proxy_user else ''
                proxy_str = f'{proxy_type}://{auth_str}{proxy_path}'
                self.proxies = {'https': proxy_str, 'http': proxy_str}

        # Load UA pool
        cache_dir = os.path.join(os.path.dirname(__file__))
        cache_path = os.path.join(cache_dir, '.ua_cache.json')
        self._ua_pool = load_ua_pool(cache_path, count=10)

        # Initialize HTTP client
        self.http_client = get_http_client(self.proxies)

    def _get_ua(self) -> str:
        return get_random_ua(self._ua_pool)

    def build_headers_and_cookies(
        self, is_image_search: bool = False
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Build request headers and cookies with full anti-detection."""
        ua = self._get_ua()

        # Swap to Chrome UA for image search
        if is_image_search and 'Chrome' not in ua:
            ua = IMAGE_USER_AGENT

        headers = {
            'User-Agent': ua,
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;'
                'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
        }

        # Add Client Hints only for Chrome-like UAs
        if 'Chrome' in ua:
            headers.update({
                'Sec-CH-UA': (
                    '"Not/A)Brand";v="8", '
                    '"Chromium";v="127", '
                    '"Google Chrome";v="127"'
                ),
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"Windows"',
            })

        cookies = {
            'CONSENT': 'PENDING+987',
            'SOCS': 'CAESHAgBEhIaAB',
        }

        return headers, cookies

    def send(self, query: str, is_image_search: bool = False):
        """Send a search request to Google."""
        base_url = self.image_search_url if is_image_search else self.search_url
        headers, cookies = self.build_headers_and_cookies(
            is_image_search=is_image_search
        )

        return self.http_client.get(
            base_url + query,
            headers=headers,
            cookies=cookies,
        )
