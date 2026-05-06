import inspect
from types import SimpleNamespace

import pytest

from dorkeye import (
    FileAnalyzer,
    DEFAULT_CONFIG,
    UserAgentRotator,
    _cmd_dry_run,
)
from sqli import HTTPFingerprintRotator


PROXY_URL = "http://127.0.0.1:8080"


# ── FileAnalyzer — proxy propagated to session ────────────────────────────────

@pytest.fixture
def proxy_config():
    cfg = DEFAULT_CONFIG.copy()
    cfg["proxy"] = PROXY_URL
    return cfg


def test_file_analyzer_session_carries_proxy(proxy_config):
    analyzer = FileAnalyzer(proxy_config, UserAgentRotator(), HTTPFingerprintRotator())
    assert analyzer.session.proxies.get("http") == PROXY_URL
    assert analyzer.session.proxies.get("https") == PROXY_URL


def test_file_analyzer_session_no_proxy_by_default():
    cfg = DEFAULT_CONFIG.copy()
    analyzer = FileAnalyzer(cfg, UserAgentRotator(), HTTPFingerprintRotator())
    assert not analyzer.session.proxies


# ── PageFetchAgent — proxy stored and propagated ──────────────────────────────

def test_page_fetch_agent_stores_proxy():
    from dorkeye_agents import PageFetchAgent
    agent = PageFetchAgent(proxy=PROXY_URL)
    assert agent.proxy == PROXY_URL


def test_page_fetch_agent_default_proxy_is_none():
    from dorkeye_agents import PageFetchAgent
    agent = PageFetchAgent()
    assert agent.proxy is None


# ── fetch_pages — proxy parameter present in signature ────────────────────────

def test_fetch_pages_accepts_proxy_kwarg():
    from dorkeye_analyze import fetch_pages
    sig = inspect.signature(fetch_pages)
    assert "proxy" in sig.parameters


# ── _cmd_dry_run — no network calls, no errors ───────────────────────────────

def _args(**kw):
    defaults = dict(dg=None, dork=None, mode="soft", output=None)
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_dry_run_with_dork_flag():
    _cmd_dry_run(["site:example.com", "inurl:admin"], _args(dork="site:example.com"))


def test_dry_run_with_dg_flag():
    _cmd_dry_run(["site:example.com"], _args(dg=["soft"]))


def test_dry_run_with_categories():
    _cmd_dry_run(
        ["site:example.com"],
        _args(dg=["soft"]),
        selected_categories=["login", "files"],
    )


def test_dry_run_empty_dork_list():
    _cmd_dry_run([], _args(dork="site:example.com"))


def test_dry_run_large_dork_list():
    dorks = [f"site:example{i}.com" for i in range(50)]
    _cmd_dry_run(dorks, _args(dork="site:example.com"))


def test_dry_run_saves_to_file(tmp_path, monkeypatch):
    out_file = "dry_run_test_output.txt"
    monkeypatch.chdir(tmp_path)
    dump_dir = tmp_path / "Dump"
    dump_dir.mkdir()

    import dorkeye as _de
    monkeypatch.setattr(_de, "__file__", str(tmp_path / "dorkeye.py"))

    _cmd_dry_run(
        ["site:example.com", "inurl:login"],
        _args(dork="site:example.com", output=out_file),
    )
    assert (dump_dir / out_file).exists()
    content = (dump_dir / out_file).read_text(encoding="utf-8")
    assert "site:example.com" in content
