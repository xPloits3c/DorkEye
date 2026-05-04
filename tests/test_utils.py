import pytest

from dorkeye import UserAgentRotator, DorkEyeEnhanced, DEFAULT_CONFIG


@pytest.fixture
def eye():
    return DorkEyeEnhanced(DEFAULT_CONFIG.copy())


# ── UserAgentRotator ──────────────────────────────────────────────────────────

def test_ua_rotator_has_agents():
    rotator = UserAgentRotator()
    assert len(rotator.agents) > 0


def test_ua_rotator_get_random_is_string():
    rotator = UserAgentRotator()
    ua = rotator.get_random()
    assert isinstance(ua, str)
    assert len(ua) > 10


def test_ua_rotator_varies():
    rotator = UserAgentRotator()
    samples = {rotator.get_random() for _ in range(30)}
    assert len(samples) > 1, "get_random() should not always return the same UA"


# ── DorkEyeEnhanced._format_size ─────────────────────────────────────────────

def test_format_size_none(eye):
    assert eye._format_size(None) == "N/A"


def test_format_size_negative(eye):
    assert eye._format_size(-1) == "N/A"


def test_format_size_bytes(eye):
    assert eye._format_size(512) == "512.0 B"


def test_format_size_kilobytes(eye):
    assert eye._format_size(1024) == "1.0 KB"


def test_format_size_megabytes(eye):
    assert eye._format_size(1024 ** 2) == "1.0 MB"


def test_format_size_gigabytes(eye):
    assert eye._format_size(1024 ** 3) == "1.0 GB"


# ── DorkEyeEnhanced._hash_url ────────────────────────────────────────────────

def test_hash_url_deterministic(eye):
    url = "https://example.com/path?q=test"
    assert eye._hash_url(url) == eye._hash_url(url)


def test_hash_url_different_inputs(eye):
    assert eye._hash_url("https://example.com") != eye._hash_url("https://other.org")


def test_hash_url_returns_string(eye):
    assert isinstance(eye._hash_url("https://example.com"), str)


# ── DorkEyeEnhanced.is_duplicate ─────────────────────────────────────────────

def test_is_duplicate_first_seen_false(eye):
    assert eye.is_duplicate("https://example.com") is False


def test_is_duplicate_second_seen_true(eye):
    url = "https://example.com/page"
    eye.is_duplicate(url)
    assert eye.is_duplicate(url) is True


def test_is_duplicate_different_urls_not_duplicate(eye):
    assert eye.is_duplicate("https://a.com") is False
    assert eye.is_duplicate("https://b.com") is False


# ── DorkEyeEnhanced.process_dorks ────────────────────────────────────────────

def test_process_dorks_single_string(eye):
    result = eye.process_dorks('site:example.com filetype:pdf')
    assert result == ['site:example.com filetype:pdf']


def test_process_dorks_from_file(eye, tmp_path):
    dork_file = tmp_path / "dorks.txt"
    dork_file.write_text("site:example.com\n# comment\ninurl:admin\n\n", encoding="utf-8")
    result = eye.process_dorks(str(dork_file))
    assert result == ["site:example.com", "inurl:admin"]


def test_process_dorks_skips_comments(eye, tmp_path):
    dork_file = tmp_path / "dorks.txt"
    dork_file.write_text("# this is a comment\ndork1\n# another\ndork2\n", encoding="utf-8")
    result = eye.process_dorks(str(dork_file))
    assert result == ["dork1", "dork2"]
