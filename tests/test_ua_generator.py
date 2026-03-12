from whoogle_lite.ua_generator import (
    generate_opera_ua,
    generate_ua_pool,
    get_random_ua,
    save_ua_pool,
    load_ua_pool,
    DEFAULT_FALLBACK_UA,
)


def test_generate_opera_ua_returns_string():
    ua = generate_opera_ua()
    assert isinstance(ua, str)
    assert len(ua) > 20


def test_generate_opera_ua_contains_opera():
    ua = generate_opera_ua()
    assert "Opera" in ua


def test_generate_opera_ua_contains_presto():
    ua = generate_opera_ua()
    assert "Presto" in ua


def test_generate_ua_pool_returns_list():
    pool = generate_ua_pool(count=5)
    assert isinstance(pool, list)
    assert len(pool) == 5


def test_generate_ua_pool_mostly_unique():
    pool = generate_ua_pool(count=10)
    # Large combinatorial space makes collisions extremely unlikely
    assert len(set(pool)) >= 8


def test_get_random_ua_from_pool():
    pool = generate_ua_pool(count=3)
    ua = get_random_ua(pool)
    assert ua in pool


def test_get_random_ua_empty_pool():
    ua = get_random_ua([])
    assert isinstance(ua, str)
    assert len(ua) > 0


def test_save_and_load_ua_pool(tmp_path):
    cache_path = str(tmp_path / "ua_cache.json")
    pool = generate_ua_pool(count=5)
    save_ua_pool(pool, cache_path)
    loaded = load_ua_pool(cache_path, count=5)
    assert loaded == pool


def test_load_ua_pool_missing_cache(tmp_path):
    cache_path = str(tmp_path / "nonexistent.json")
    pool = load_ua_pool(cache_path, count=3)
    assert len(pool) == 3
    assert all("Opera" in ua for ua in pool)


def test_default_fallback_ua():
    assert "Opera" in DEFAULT_FALLBACK_UA
