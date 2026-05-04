import pytest

from dorkeye_patterns import label_from_score, censor, luhn_check, SCORE_TO_LABEL


# ── label_from_score ──────────────────────────────────────────────────────────

def test_score_to_label_thresholds_are_descending():
    scores = [t[0] for t in SCORE_TO_LABEL]
    assert scores == sorted(scores, reverse=True)


def test_label_critical():
    assert label_from_score(90) == "CRITICAL"
    assert label_from_score(100) == "CRITICAL"


def test_label_high():
    assert label_from_score(70) == "HIGH"
    assert label_from_score(89) == "HIGH"


def test_label_medium():
    assert label_from_score(50) == "MEDIUM"
    assert label_from_score(69) == "MEDIUM"


def test_label_low():
    assert label_from_score(20) == "LOW"
    assert label_from_score(49) == "LOW"


def test_label_skip():
    assert label_from_score(0) == "SKIP"
    assert label_from_score(19) == "SKIP"


def test_label_boundary_values():
    for threshold, label in SCORE_TO_LABEL:
        assert label_from_score(threshold) == label


# ── censor ────────────────────────────────────────────────────────────────────

def test_censor_short_value_all_masked():
    result = censor("ab12")
    assert result == "****"


def test_censor_long_value_shows_ends():
    result = censor("sk-abc123xyz456789")
    assert result.startswith("sk-a")
    assert result.endswith("6789")
    assert "…" in result


def test_censor_custom_show():
    result = censor("abcdefghijklmnop", show=2)
    assert result.startswith("ab")
    assert result.endswith("op")


def test_censor_preserves_length_info():
    short = censor("ab")
    long_ = censor("abcdefghijklmnopqrstuvwxyz")
    assert len(short) < len(long_)


# ── luhn_check ────────────────────────────────────────────────────────────────

def test_luhn_valid_visa():
    assert luhn_check("4532015112830366") is True


def test_luhn_valid_mastercard():
    assert luhn_check("5425233430109903") is True


def test_luhn_invalid_number():
    assert luhn_check("1234567890123456") is False


def test_luhn_empty_string():
    assert luhn_check("") is False


def test_luhn_too_short():
    assert luhn_check("123456789012") is False


def test_luhn_ignores_spaces_and_dashes():
    assert luhn_check("4532-0151-1283-0366") is True
    assert luhn_check("4532 0151 1283 0366") is True
