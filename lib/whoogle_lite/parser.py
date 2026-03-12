"""Google HTML result parser — extracts search results as structured data.

Includes pieces from Whoogle's app/utils/results.py (filter_link_args,
has_ad_content) plus new HTML parsing logic for extracting results from
Google's gbv=1 basic HTML mode.
"""

import re
import urllib.parse as urlparse
from typing import Dict, List, Optional

from bs4 import BeautifulSoup


# Tracking/ad params to strip from result URLs
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_cid', 'utm_reader', 'utm_name', 'utm_viz_id', 'utm_pubreferrer',
    'utm_swu', 'utm_referrer', 'ref_src',
    'sa', 'ved', 'usg', 'ei', 'sei',
}

# Multilingual ad keywords (from Whoogle's results.py)
AD_KEYWORDS = {
    'Ad', 'Ads', 'Sponsored', 'Anzeige', 'Anzeigen',
    'Annonce', 'Annonces', 'Sponsorisé',
    'Anuncio', 'Anuncios', 'Patrocinado',
    'Annuncio', 'Sponsorizzato',
    'Advertentie', 'Gesponsord',
    'Реклама', 'Оголошення',
    '広告', '赞助', '스폰서',
}

# CAPTCHA detection string (from Whoogle's search.py)
CAPTCHA_MARKER = 'div class="g-recaptcha"'

# Result container CSS classes (tiered fallback)
PRIMARY_SELECTORS = ['div.ZINbbc', 'div.ezO2md']
SECONDARY_SELECTORS = ['div.g', 'div.tF2Cxc']


def has_captcha(html: str) -> bool:
    """Check if Google returned a CAPTCHA page."""
    return CAPTCHA_MARKER in html


def has_ad_content(text: str) -> bool:
    """Check if text contains ad/sponsored indicators.

    Uses word-boundary matching to avoid false positives
    (e.g., "Adobe" should not match "Ad").
    """
    words = set(text.split())
    return bool(words & AD_KEYWORDS)


def filter_link_args(url: str) -> str:
    """Remove tracking parameters from a URL."""
    if '?' not in url:
        return url
    parsed = urlparse.urlparse(url)
    params = urlparse.parse_qs(parsed.query, keep_blank_values=True)
    filtered = {k: v for k, v in params.items() if k not in TRACKING_PARAMS}
    if not filtered:
        return urlparse.urlunparse(parsed._replace(query=''))
    new_query = urlparse.urlencode(filtered, doseq=True)
    return urlparse.urlunparse(parsed._replace(query=new_query))


def _extract_url_from_href(href: str) -> Optional[str]:
    """Extract the real URL from a Google redirect wrapper."""
    if not href:
        return None

    if href.startswith('/url?'):
        parsed = urlparse.urlparse(href)
        params = urlparse.parse_qs(parsed.query)
        q_vals = params.get('q', [])
        if q_vals:
            return filter_link_args(q_vals[0])
        return None

    if href.startswith('http'):
        return filter_link_args(href)

    return None


def _extract_text(element) -> str:
    """Extract visible text from a BeautifulSoup element."""
    if element is None:
        return ''
    return element.get_text(separator=' ', strip=True)


def _is_ad_result(container) -> bool:
    """Check if a result container is an advertisement."""
    text = _extract_text(container)
    prefix = text[:80] if text else ''
    return has_ad_content(prefix)


def _parse_primary(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Parse results using primary selectors (gbv=1 basic mode)."""
    results = []
    for selector in PRIMARY_SELECTORS:
        containers = soup.select(selector)
        if not containers:
            continue
        for container in containers:
            if _is_ad_result(container):
                continue
            link = container.find('a', href=True)
            if not link:
                continue
            url = _extract_url_from_href(link.get('href', ''))
            if not url or not url.startswith('http'):
                continue
            title = _extract_text(link)
            snippet_parts = []
            for div in container.find_all('div', recursive=False):
                if div.find('a') is None:
                    text = _extract_text(div)
                    if text and text != title:
                        snippet_parts.append(text)
            snippet = ' '.join(snippet_parts)
            results.append({
                'title': title,
                'url': url,
                'snippet': snippet,
            })
        if results:
            return results
    return results


def _parse_secondary(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Parse results using secondary selectors (standard Google)."""
    results = []
    for selector in SECONDARY_SELECTORS:
        containers = soup.select(selector)
        if not containers:
            continue
        for container in containers:
            if _is_ad_result(container):
                continue
            link = container.find('a', href=True)
            if not link:
                continue
            url = _extract_url_from_href(link.get('href', ''))
            if not url or not url.startswith('http'):
                continue
            title = _extract_text(link.find('h3')) or _extract_text(link)
            snippet_el = container.select_one('div.VwiC3b, div.IsZvec, span.aCOpRe')
            snippet = _extract_text(snippet_el) if snippet_el else ''
            results.append({
                'title': title,
                'url': url,
                'snippet': snippet,
            })
        if results:
            return results
    return results


def _parse_tertiary(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Tertiary fallback: extract any links that look like search results."""
    results = []
    seen_urls = set()
    for link in soup.find_all('a', href=True):
        url = _extract_url_from_href(link.get('href', ''))
        if not url or not url.startswith('http'):
            continue
        parsed = urlparse.urlparse(url)
        if parsed.hostname and 'google' in parsed.hostname:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        title = _extract_text(link)
        if not title or len(title) < 3:
            continue
        results.append({
            'title': title,
            'url': url,
            'snippet': '',
        })
    return results


def parse_results(html: str, num: int = 10) -> List[Dict[str, str]]:
    """Parse Google search HTML and extract results as structured data.

    Uses tiered CSS selector fallbacks:
    1. Primary: div.ZINbbc / div.ezO2md (gbv=1 basic mode)
    2. Secondary: div.g / div.tF2Cxc (standard Google)
    3. Tertiary: generic <a> link extraction
    """
    if has_captcha(html):
        return []

    soup = BeautifulSoup(html, 'html.parser')

    results = _parse_primary(soup)
    if not results:
        results = _parse_secondary(soup)
    if not results:
        results = _parse_tertiary(soup)

    return results[:num]
