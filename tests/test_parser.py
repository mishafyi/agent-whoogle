from whoogle_lite.parser import parse_results, has_captcha, filter_link_args, has_ad_content


SAMPLE_RESULT_HTML = '''
<html><body>
<div class="ZINbbc">
  <div class="kCrYT"><a href="/url?q=https://example.com/page1&amp;sa=U"><div class="BNeawe">Example Title 1</div></a></div>
  <div class="BNeawe">This is a snippet for the first result.</div>
</div>
<div class="ZINbbc">
  <div class="kCrYT"><a href="/url?q=https://example.com/page2&amp;sa=U"><div class="BNeawe">Example Title 2</div></a></div>
  <div class="BNeawe">This is a snippet for the second result.</div>
</div>
</body></html>
'''

CAPTCHA_HTML = '''
<html><body>
<div class="g-recaptcha"></div>
</body></html>
'''

AD_HTML = '''
<html><body>
<div class="ZINbbc">
  <div>Sponsored</div>
  <div class="kCrYT"><a href="/url?q=https://ad.example.com&amp;sa=U"><div class="BNeawe">Ad Title</div></a></div>
</div>
</body></html>
'''


def test_parse_results_basic():
    results = parse_results(SAMPLE_RESULT_HTML)
    assert len(results) >= 1
    assert results[0]["url"] == "https://example.com/page1"
    assert "Example Title 1" in results[0]["title"]


def test_parse_results_strips_google_redirect():
    results = parse_results(SAMPLE_RESULT_HTML)
    for r in results:
        assert "/url?q=" not in r["url"]
        assert "&sa=" not in r["url"]


def test_has_captcha_true():
    assert has_captcha(CAPTCHA_HTML) is True


def test_has_captcha_false():
    assert has_captcha(SAMPLE_RESULT_HTML) is False


def test_filter_link_args():
    dirty = "https://example.com/page?utm_source=google&utm_medium=cpc&real_param=value"
    clean = filter_link_args(dirty)
    assert "utm_source" not in clean
    assert "utm_medium" not in clean
    assert "real_param=value" in clean


def test_filter_link_args_no_params():
    url = "https://example.com/page"
    assert filter_link_args(url) == url


def test_has_ad_content_true():
    assert has_ad_content("Sponsored") is True
    assert has_ad_content("Ad") is True


def test_has_ad_content_false():
    assert has_ad_content("Regular result text") is False


def test_has_ad_content_no_false_positive():
    # "Adobe" contains "Ad" but should not match
    assert has_ad_content("Adobe Photoshop Tutorial") is False


def test_parse_results_empty_html():
    results = parse_results("<html><body></body></html>")
    assert results == []


def test_parse_results_captcha_returns_empty():
    results = parse_results(CAPTCHA_HTML)
    assert results == []
