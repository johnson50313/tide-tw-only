from pipeline.extract import extract_tpex_insti, extract_tpex_otc, is_stock
from pipeline.parsers import to_number


def test_extract_tpex_insti_rows(tpex_insti_raw):
    rows = extract_tpex_insti(tpex_insti_raw)
    assert len(rows) == 886
    assert all(r["market"] == "TPEX" for r in rows)


def test_extract_tpex_insti_known_row(tpex_insti_raw):
    rows = {r["code"]: r for r in extract_tpex_insti(tpex_insti_raw)}
    sas = rows["5483"]
    assert sas["name"] == "中美晶"
    assert sas["net_shares"] == 4250116.0


def test_tpex_total_identity(tpex_insti_raw):
    """三大法人合計 == 外資合計 + 投信 + 自營商合計。

    此恆等式在 886 列上零違反；違反即表示欄位索引錯位。
    """
    for row in tpex_insti_raw["tables"][0]["data"]:
        parts = to_number(row[10]) + to_number(row[13]) + to_number(row[22])
        assert abs(parts - to_number(row[23])) < 0.5, row[0]


def test_tpex_foreign_identity(tpex_insti_raw):
    """外資合計 == 外陸資(不含外資自營商) + 外資自營商。"""
    for row in tpex_insti_raw["tables"][0]["data"]:
        parts = to_number(row[4]) + to_number(row[7])
        assert abs(parts - to_number(row[10])) < 0.5, row[0]


def test_tpex_dealer_identity(tpex_insti_raw):
    """自營商合計 == 自行買賣 + 避險。"""
    for row in tpex_insti_raw["tables"][0]["data"]:
        parts = to_number(row[16]) + to_number(row[19])
        assert abs(parts - to_number(row[22])) < 0.5, row[0]


def test_extract_tpex_otc(tpex_otc_raw):
    prices = extract_tpex_otc(tpex_otc_raw)
    assert len(prices) == 1014
    assert prices["5483"]["name"] == "中美晶"
    assert prices["5483"]["close"] == 183.5
    assert prices["5483"]["chg"] == 7.5


def test_tpex_otc_stock_codes_are_strings(tpex_otc_raw):
    prices = extract_tpex_otc(tpex_otc_raw)
    assert all(isinstance(c, str) for c in prices)
    assert any(is_stock(c) for c in prices)
