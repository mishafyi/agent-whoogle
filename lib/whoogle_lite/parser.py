"""Google HTML result parser — ported from Whoogle Search.

Source files:
- app/filter.py (Filter class — ad removal, AI overview removal, link rewriting, CSS normalization)
- app/models/g_classes.py (GClasses — CSS class mapping for Google's obfuscated names)
- app/routes.py (JSON extraction — structured result parsing from filtered HTML)
- app/utils/results.py (has_ad_content, filter_link_args — utility functions)

Removed (not needed for CLI search):
- Flask/Fernet encryption, favicon injection, site alt swaps, image proxying,
  CSS rewriting, anonymous view, dark theme toggle, config/session handling,
  collapse_sections, block_titles/url/tabs, image search parsing
"""

import re
import urllib.parse as urlparse
from urllib.parse import parse_qs
from typing import Dict, List

from bs4 import BeautifulSoup
from bs4.element import Tag


# ---------------------------------------------------------------------------
# From app/utils/results.py
# ---------------------------------------------------------------------------

SKIP_ARGS = ['ref_src', 'utm']

BLACKLIST = [
    'ad', 'ads', 'anuncio', 'annuncio', 'annonce', 'Anzeige', '广告', '廣告',
    'Reklama', 'Реклама', 'Anunț', '광고', 'annons', 'Annonse', 'Iklan',
    '広告', 'Augl.', 'Mainos', 'Advertentie', 'إعلان', 'Գովազդ', 'विज्ञापन',
    'Reklam', 'آگهی', 'Reklāma', 'Reklaam', 'Διαφήμιση', 'מודעה', 'Hirdetés',
    'Anúncio', 'Quảng cáo', 'โฆษณา', 'sponsored', 'patrocinado', 'gesponsert',
    'Sponzorováno', '스폰서', 'Gesponsord', 'Sponsorisé',
]


def has_ad_content(element: str) -> bool:
    """Inspects an HTML element for ad related content

    Args:
        element: The HTML element to inspect

    Returns:
        bool: True/False for the element containing an ad

    """
    element_str = ''.join(filter(str.isalpha, element))
    return (element_str.upper() in (value.upper() for value in BLACKLIST)
            or 'ⓘ' in element)


def filter_link_args(link: str) -> str:
    """Filters out unnecessary URL args from a result link

    Args:
        link: The string result link to check for extraneous URL params

    Returns:
        str: An updated (or ignored) result link

    """
    parsed_link = urlparse.urlparse(link)
    link_args = parse_qs(parsed_link.query)
    safe_args = {}

    if len(link_args) == 0 and len(parsed_link) > 0:
        return link

    for arg in link_args.keys():
        if arg in SKIP_ARGS:
            continue

        safe_args[arg] = link_args[arg]

    # Remove original link query and replace with filtered args
    link = link.replace(parsed_link.query, '')
    if len(safe_args) > 0:
        link = link + urlparse.urlencode(safe_args, doseq=True)
    else:
        link = link.replace('?', '')

    return link


# ---------------------------------------------------------------------------
# From app/models/g_classes.py
# ---------------------------------------------------------------------------

class GClasses:
    """Tracking obfuscated class names used in Google results.

    Note: Using these should be a last resort. It is always preferred to filter
    results using structural cues instead of referencing class names, as these
    are liable to change at any moment.
    """
    main_tbm_tab = 'KP7LCb'
    images_tbm_tab = 'n692Zd'
    footer = 'TuS8Ad'
    result_class_a = 'ZINbbc'
    result_class_b = 'luh4td'
    scroller_class = 'idg8be'
    line_tag = 'BsXmcf'

    result_classes = {
        result_class_a: ['Gx5Zad'],
        result_class_b: ['fP1Qef'],
    }

    @classmethod
    def replace_css_classes(cls, soup: BeautifulSoup) -> BeautifulSoup:
        """Replace updated Google classes with the original class names that
        Whoogle relies on for styling.

        Args:
            soup: The result page as a BeautifulSoup object

        Returns:
            BeautifulSoup: The new BeautifulSoup
        """
        result_divs = soup.find_all('div', {
            'class': [_ for c in cls.result_classes.values() for _ in c]
        })

        for div in result_divs:
            new_class = ' '.join(div['class'])
            for key, val in cls.result_classes.items():
                new_class = ' '.join(new_class.replace(_, key) for _ in val)
            div['class'] = new_class.split(' ')
        return soup


# ---------------------------------------------------------------------------
# From app/filter.py — extract_q, Filter (trimmed)
# ---------------------------------------------------------------------------

CAPTCHA_MARKER = 'div class="g-recaptcha"'

unsupported_g_pages = [
    'support.google.com',
    'accounts.google.com',
    'policies.google.com',
    'google.com/preferences',
    'google.com/intl',
    'advanced_search',
    'tbm=shop',
    'ageverification.google.co.kr',
]


def has_captcha(html: str) -> bool:
    """Check if Google returned a CAPTCHA page."""
    return CAPTCHA_MARKER in html


def extract_q(q_str: str, href: str) -> str:
    """Extracts the 'q' element from a result link."""
    return parse_qs(q_str, keep_blank_values=True)['q'][0] \
        if ('&q=' in href or '?q=' in href) else ''


class Filter:
    """Trimmed version of Whoogle's Filter class.

    Only keeps methods needed for structured result extraction:
    - remove_ads
    - remove_ai_overview
    - update_styling (CSS class normalization)
    - update_link (link rewriting / redirect stripping)
    - sanitize_div
    """

    def __init__(self) -> None:
        self.soup = None
        self.main_divs = None

    def clean(self, soup: BeautifulSoup) -> BeautifulSoup:
        self.soup = soup
        self.main_divs = self.soup.find('div', {'id': 'main'})
        self.remove_ads()
        self.remove_ai_overview()
        self.update_styling()

        if self.main_divs:
            for div in self.main_divs:
                self.sanitize_div(div)

        for link in self.soup.find_all('a', href=True):
            self.update_link(link)

        # Ensure no extra scripts passed through
        for script in self.soup('script'):
            script.decompose()

        return self.soup

    def sanitize_div(self, div) -> None:
        """Removes escaped script and iframe tags from results"""
        import html as html_mod
        if not div or not isinstance(div, Tag):
            return

        for d in div.find_all('div', recursive=True):
            d_text = d.find(string=True, recursive=False)

            if not d_text or not d.string:
                continue

            d.string = html_mod.unescape(d_text)
            div_soup = BeautifulSoup(d.string, 'html.parser')

            for script in div_soup.find_all('script'):
                script.decompose()

            for iframe in div_soup.find_all('iframe'):
                iframe.decompose()

            d.string = str(div_soup)

    def remove_ads(self) -> None:
        """Removes ads found in the list of search result divs"""
        if not self.main_divs:
            return

        for div in [_ for _ in self.main_divs.find_all('div', recursive=True)]:
            div_ads = [_ for _ in div.find_all('span', recursive=True)
                       if has_ad_content(_.text)]
            _ = div.decompose() if len(div_ads) else None

    def remove_ai_overview(self) -> None:
        """Removes Google's AI Overview/SGE results from search results"""
        if not self.main_divs:
            return

        ai_patterns = [
            'AI Overview',
            'AI responses may include mistakes',
        ]

        result_classes = [GClasses.result_class_a]
        result_classes.extend(GClasses.result_classes.get(
            GClasses.result_class_a, []))

        divs_to_remove = []

        for div in self.main_divs.find_all('div', recursive=True):
            div_text = div.get_text()
            if any(pattern in div_text for pattern in ai_patterns):
                parent = div
                while parent:
                    p_cls = parent.attrs.get('class') or []
                    if any(rc in p_cls for rc in result_classes):
                        if parent not in divs_to_remove:
                            divs_to_remove.append(parent)
                        break
                    parent = parent.parent

        for div in divs_to_remove:
            div.decompose()

    def update_styling(self) -> None:
        """Update CSS classes for result divs"""
        GClasses.replace_css_classes(self.soup)

    def update_link(self, link: Tag) -> None:
        """Rewrite links: strip Google redirects and tracking params.

        Trimmed from Whoogle's update_link — removed encryption, favicon,
        anon view, config-dependent logic. Kept redirect stripping and
        unsupported page removal.
        """
        parsed_link = urlparse.urlparse(link['href'])
        if '/url?q=' in link['href']:
            link_netloc = extract_q(parsed_link.query, link['href'])
        else:
            link_netloc = parsed_link.netloc

        # Remove elements that direct to unsupported Google pages
        if any(url in link_netloc for url in unsupported_g_pages):
            link['href'] = link_netloc
            parent = link.parent
            while parent:
                p_cls = parent.attrs.get('class') or []
                if f'{GClasses.result_class_a}' in p_cls:
                    parent.decompose()
                    break
                parent = parent.parent
            if link.decomposed:
                return

        # Replace href with only the intended destination
        href = link['href'].replace('https://www.google.com', '')
        result_link = urlparse.urlparse(href)
        q = extract_q(result_link.query, href)

        if q.startswith('/') and 'spell=1' not in href:
            link['href'] = 'https://google.com' + q
        elif q.startswith('https://accounts.google.com'):
            link.decompose()
            return
        elif 'url?q=' in href:
            # Strip unneeded arguments — this is the main case for result links
            link['href'] = filter_link_args(q)
        else:
            link['href'] = href


# ---------------------------------------------------------------------------
# From app/routes.py — clean_text_spacing, JSON extraction
# ---------------------------------------------------------------------------

def clean_text_spacing(text: str) -> str:
    """Clean up text spacing issues from HTML extraction."""
    if not text:
        return text

    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)

    # Fix domain names: "weather .com" -> "weather.com"
    text = re.sub(r'\s+\.([a-zA-Z]{2,})\b', r'.\1', text)

    # Fix www/http/https patterns: "www .example" -> "www.example"
    text = re.sub(r'\b(www|http|https)\s+\.', r'\1.', text)

    # Fix spaces before common punctuation
    text = re.sub(r'\s+([,;:])', r'\1', text)

    return text.strip()


def _extract_json_results(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract structured results from filtered soup.

    Ported directly from Whoogle's routes.py JSON extraction block
    (the `if wants_json:` branch of the /search route).
    """
    results = []
    seen = set()

    # Find all result containers (using known result classes)
    result_divs = soup.find_all('div', class_=['ZINbbc', 'ezO2md'])

    if result_divs:
        # Process structured Google results with container divs
        for div in result_divs:
            # Find the first valid link in this result container
            link = None
            for a in div.find_all('a', href=True):
                if a['href'].startswith('http'):
                    link = a
                    break

            if not link:
                continue

            href = link['href']
            if href in seen:
                continue

            # Get all text from the result container
            text = clean_text_spacing(div.get_text(separator=' ', strip=True))
            if not text:
                continue

            # Extract title: h3 > span.CVA68e > link text
            title = ''
            h3_tag = div.find('h3')
            if h3_tag:
                title = clean_text_spacing(
                    h3_tag.get_text(separator=' ', strip=True))
            else:
                title_span = div.find('span', class_='CVA68e')
                if title_span:
                    title = clean_text_spacing(
                        title_span.get_text(separator=' ', strip=True))
                elif link:
                    title = clean_text_spacing(
                        link.get_text(separator=' ', strip=True))

            # Extract snippet
            content = ''
            snippet_selectors = [
                {'class_': 'VwiC3b'},
                {'class_': 'FrIlee'},
                {'class_': 's'},
                {'class_': 'st'},
            ]

            for selector in snippet_selectors:
                snippet_elem = (div.find('span', selector)
                                or div.find('div', selector))
                if snippet_elem:
                    content = clean_text_spacing(
                        snippet_elem.get_text(separator=' ', strip=True))
                    if (content and not content.startswith('www.')
                            and '›' not in content):
                        break
                    else:
                        content = ''

            # Fallback: full text minus title
            if not content and title:
                if text.startswith(title):
                    content = text[len(title):].strip()
                else:
                    content = text
            elif not content:
                content = text

            seen.add(href)
            results.append({
                'title': title,
                'url': href,
                'snippet': content,
            })
    else:
        # Fallback: extract links directly if no result containers found
        for a in soup.find_all('a', href=True):
            href = a['href']
            if not href.startswith('http'):
                continue
            # Skip google.com links
            parsed = urlparse.urlparse(href)
            if parsed.hostname and 'google' in parsed.hostname:
                continue
            if href in seen:
                continue
            text = clean_text_spacing(a.get_text(separator=' ', strip=True))
            if not text or len(text) < 3:
                continue
            seen.add(href)
            results.append({
                'title': text,
                'url': href,
                'snippet': '',
            })

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_results(html: str, num: int = 10) -> List[Dict[str, str]]:
    """Parse Google search HTML and extract results as structured data.

    Pipeline (mirrors Whoogle):
    1. Filter.clean() — remove ads, AI overview, normalize CSS, rewrite links
    2. _extract_json_results() — extract structured results from filtered HTML
    """
    if has_captcha(html):
        return []

    soup = BeautifulSoup(html, 'html.parser')

    # Run Whoogle's filter pipeline
    f = Filter()
    soup = f.clean(soup)

    # Extract structured results (from routes.py JSON branch)
    results = _extract_json_results(soup)

    return results[:num]
