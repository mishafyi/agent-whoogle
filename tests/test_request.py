from whoogle_lite.request import WhoogleRequest, build_query


def test_build_query_basic():
    q = build_query("hello world")
    assert "hello" in q
    assert "world" in q
    assert "safe=off" in q


def test_build_query_with_lang():
    q = build_query("test", lang="lang_en")
    assert "lr=lang_en" in q


def test_build_query_with_country():
    q = build_query("test", country="US")
    assert "gl=US" in q


def test_build_query_with_safe():
    q = build_query("test", safe=True)
    assert "safe=active" in q


def test_build_query_with_time_filter():
    q = build_query("test", time_range="week")
    assert "tbs=qdr:w" in q


def test_build_query_with_start():
    q = build_query("test", start=10)
    assert "start=10" in q


def test_build_query_with_num():
    q = build_query("test", num=20)
    assert "num=20" in q


def test_build_query_default_num_omitted():
    q = build_query("test")
    assert "num=" not in q


def test_request_headers():
    req = WhoogleRequest()
    headers, cookies = req.build_headers_and_cookies()
    assert "User-Agent" in headers
    assert "Opera" in headers["User-Agent"] or "Chrome" in headers["User-Agent"]
    assert headers["Sec-Fetch-Site"] == "none"
    assert headers["Sec-Fetch-Mode"] == "navigate"
    assert cookies["CONSENT"] == "PENDING+987"
    assert cookies["SOCS"] == "CAESHAgBEhIaAB"


def test_request_image_search_uses_chrome_ua():
    req = WhoogleRequest()
    headers, _ = req.build_headers_and_cookies(is_image_search=True)
    assert "Chrome" in headers["User-Agent"]
    assert "Sec-CH-UA" in headers


def test_request_search_url():
    req = WhoogleRequest()
    assert req.search_url == "https://www.google.com/search?gbv=1&q="


def test_request_image_search_url():
    req = WhoogleRequest()
    assert req.image_search_url == "https://www.google.com/search?udm=2&q="


def test_request_send(httpserver):
    httpserver.expect_request("/search").respond_with_data("<html>results</html>")
    req = WhoogleRequest()
    req.search_url = httpserver.url_for("/search") + "?q="
    response = req.send(query="test")
    assert response.status_code == 200


def test_request_proxy_from_cli():
    req = WhoogleRequest(proxy="socks5://127.0.0.1:9050")
    assert req.proxies.get("https") == "socks5://127.0.0.1:9050"
