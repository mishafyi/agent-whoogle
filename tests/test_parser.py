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


# GBV1 layout (div.Gx5Zad.xpd.EtOod.pkphOe) — observed on datacenter IPs
GBV1_HTML = '''
<html><body><div id="main">
<div class="Gx5Zad xpd EtOod pkphOe">
  <div class="egMi0 kCrYT">
    <a href="/url?q=https://example.com/gbv1-page&amp;sa=U">
      Example GBV1 Title - Sitename example.com
    </a>
  </div>
  <div class="kCrYT">
    <div class="BNeawe">This is the snippet from the gbv1 layout.</div>
  </div>
</div>
<div class="Gx5Zad xpd EtOod pkphOe">
  <div class="kCrYT">
    <a href="/url?q=https://example.com/gbv1-page2&amp;sa=U">
      Second GBV1 Result - Other Site
    </a>
  </div>
  <div class="kCrYT">
    <div>Another snippet here with details.</div>
  </div>
</div>
</div></body></html>
'''


def test_parse_gbv1_layout():
    results = parse_results(GBV1_HTML)
    assert len(results) == 2
    assert results[0]["url"] == "https://example.com/gbv1-page"
    assert "GBV1 Title" in results[0]["title"]
    assert "snippet from the gbv1 layout" in results[0]["snippet"]
    assert results[1]["url"] == "https://example.com/gbv1-page2"
    assert results[1]["snippet"] != ""


def test_parse_gbv1_filters_ads():
    ad_gbv1 = '''
    <html><body><div id="main">
    <div class="Gx5Zad xpd EtOod pkphOe">
      <div>Sponsored</div>
      <div class="kCrYT">
        <a href="/url?q=https://ad.example.com&amp;sa=U">Ad Result</a>
      </div>
    </div>
    <div class="Gx5Zad xpd EtOod pkphOe">
      <div class="kCrYT">
        <a href="/url?q=https://real.example.com&amp;sa=U">Real Result Title</a>
      </div>
      <div class="kCrYT">Real snippet text.</div>
    </div>
    </div></body></html>
    '''
    results = parse_results(ad_gbv1)
    assert len(results) == 1
    assert results[0]["url"] == "https://real.example.com"


def test_parse_ad_html_filtered():
    """Test that the AD_HTML sample has its ad results filtered out."""
    results = parse_results(AD_HTML)
    for r in results:
        assert "ad.example.com" not in r["url"]
