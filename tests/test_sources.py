from pipeline.sources import build_url, is_empty


def test_build_url_twse_uses_compact_date():
    url = build_url("t86", "2026-09-16")
    assert "date=20260916" in url
    assert "selectType=ALL" in url


def test_build_url_tpex_uses_slash_date():
    url = build_url("tpex_insti", "2026-09-16")
    assert "date=2026/09/16" in url


def test_build_url_rejects_unknown_kind():
    import pytest

    with pytest.raises(KeyError):
        build_url("nope", "2026-09-16")


def test_is_empty_detects_holiday_twse():
    assert is_empty("t86", {"stat": "OK", "data": []}) is True
    assert is_empty("t86", {"stat": "OK", "data": [["2330"]]}) is False
    assert is_empty("mi_index", {"stat": "OK", "tables": []}) is True
    assert is_empty("mi_index", {"stat": "很抱歉，沒有符合條件的資料!"}) is True


def test_is_empty_detects_holiday_tpex():
    assert is_empty("tpex_insti", {"tables": [{"data": []}]}) is True
    assert is_empty("tpex_insti", {"tables": []}) is True
    assert is_empty("tpex_insti", {"tables": [{"data": [["5483"]]}]}) is False


def test_is_empty_on_real_fixtures(t86_raw, mi_index_raw, bfi_raw, tpex_insti_raw, tpex_otc_raw):
    assert is_empty("t86", t86_raw) is False
    assert is_empty("mi_index", mi_index_raw) is False
    assert is_empty("bfi", bfi_raw) is False
    assert is_empty("tpex_insti", tpex_insti_raw) is False
    assert is_empty("tpex_otc", tpex_otc_raw) is False
