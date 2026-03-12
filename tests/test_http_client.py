from whoogle_lite.http_client import HttpxClient


def test_client_creation():
    client = HttpxClient(http2=False)
    assert client is not None
    client.close()


def test_client_get_success(httpserver):
    """Uses pytest-httpserver to test a real GET request."""
    httpserver.expect_request("/test").respond_with_data("hello", status=200)
    client = HttpxClient(http2=False)
    response = client.get(httpserver.url_for("/test"))
    assert response.status_code == 200
    assert response.text == "hello"
    client.close()


def test_client_retry_on_failure(httpserver):
    """First request fails, second succeeds."""
    httpserver.expect_ordered_request("/retry").respond_with_data("", status=500)
    httpserver.expect_ordered_request("/retry").respond_with_data("ok", status=200)
    client = HttpxClient(http2=False)
    # Should succeed on retry
    response = client.get(httpserver.url_for("/retry"), retries=1, backoff_seconds=0.01)
    client.close()


def test_client_proxies_property():
    client = HttpxClient(proxies={"http": "http://proxy:8080"}, http2=False)
    assert client.proxies == {"http": "http://proxy:8080"}
    client.close()


def test_client_caching(httpserver):
    httpserver.expect_request("/cached").respond_with_data("cached_data", status=200)
    client = HttpxClient(http2=False, cache_ttl_seconds=60)
    r1 = client.get(httpserver.url_for("/cached"), use_cache=True)
    r2 = client.get(httpserver.url_for("/cached"), use_cache=True)
    assert r1.text == r2.text
    client.close()


from whoogle_lite.provider import get_http_client, close_all_clients


def test_provider_returns_client():
    client = get_http_client({})
    assert client is not None
    close_all_clients()


def test_provider_caches_same_proxy():
    c1 = get_http_client({})
    c2 = get_http_client({})
    assert c1 is c2
    close_all_clients()


def test_provider_different_proxy():
    c1 = get_http_client({})
    c2 = get_http_client({"http": "http://proxy:8080"})
    assert c1 is not c2
    close_all_clients()
