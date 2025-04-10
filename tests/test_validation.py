from page_analyzer.app import validate_and_normalize_url
import pytest


def test_validate_and_normalize_url():
    assert validate_and_normalize_url("https://example.com") == "https://example.com"
    assert validate_and_normalize_url("http://test.ru/path") == "http://test.ru"

    with pytest.raises(ValueError):
        validate_and_normalize_url("not-a-url")

    with pytest.raises(ValueError):
        validate_and_normalize_url("")
