import pytest

from pipeline.sectors import all_codes, load_sectors


@pytest.fixture(scope="session")
def sectors():
    return load_sectors()


def test_sector_count(sectors):
    assert len(sectors) == 76


def test_unique_code_count(sectors):
    assert len(all_codes(sectors)) == 601


def test_codes_are_strings(sectors):
    for name, codes in sectors.items():
        for code in codes:
            assert isinstance(code, str), f"{name} 的 {code!r} 不是字串"


def test_no_empty_sector(sectors):
    for name, codes in sectors.items():
        assert len(codes) > 0, f"{name} 沒有成分股"


def test_no_duplicate_within_sector(sectors):
    for name, codes in sectors.items():
        assert len(codes) == len(set(codes)), f"{name} 有重複代號"


def test_known_sector_membership(sectors):
    assert "2317" in sectors["AI 伺服器組裝"]
    assert "3706" in sectors["AI 伺服器組裝"]   # 神達，已由 2315 替換
    assert "2315" not in all_codes(sectors)     # 舊代號應已清除
    assert "3576" in sectors["太陽能產業"]       # 聯合再生
