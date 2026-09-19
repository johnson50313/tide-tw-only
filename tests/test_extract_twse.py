from pipeline.extract import extract_mi_index, extract_t86, is_stock
from pipeline.parsers import to_number


def test_is_stock():
    assert is_stock("2330") is True
    assert is_stock("0050") is True
    assert is_stock("031234") is False   # 權證，6 位
    assert is_stock("00411A") is False   # 含英文
    assert is_stock("12345") is False    # 5 位


def test_extract_t86_returns_all_rows(t86_raw):
    rows = extract_t86(t86_raw)
    assert len(rows) == 16893
    assert all(isinstance(r["code"], str) for r in rows)
    assert all(r["market"] == "TWSE" for r in rows)


def test_extract_t86_known_row(t86_raw):
    rows = {r["code"]: r for r in extract_t86(t86_raw)}
    au = rows["2409"]
    assert au["name"] == "友達"
    assert au["net_shares"] == 56611082.0


def test_extract_t86_stock_count(t86_raw):
    rows = extract_t86(t86_raw)
    assert sum(1 for r in rows if is_stock(r["code"])) == 1075


def test_t86_column_identity(t86_raw):
    """三大法人 == 外陸資 + 外資自營商 + 投信 + 自營商。

    此恆等式在 16893 列上零違反；違反即表示欄位索引錯位。
    """
    for row in t86_raw["data"]:
        parts = to_number(row[4]) + to_number(row[7]) + to_number(row[10]) + to_number(row[11])
        assert abs(parts - to_number(row[18])) < 0.5, row[0]


def test_t86_dealer_identity(t86_raw):
    """自營商買賣超 == 自行買賣 + 避險。"""
    for row in t86_raw["data"]:
        parts = to_number(row[14]) + to_number(row[17])
        assert abs(parts - to_number(row[11])) < 0.5, row[0]


def test_extract_mi_index(mi_index_raw):
    prices = extract_mi_index(mi_index_raw)
    assert prices["2330"]["name"] == "台積電"
    assert prices["2330"]["close"] == 2380.0
    assert prices["2330"]["chg"] == 0.0
    assert sum(1 for c in prices if is_stock(c)) == 1092


def test_extract_mi_index_strips_html(mi_index_raw):
    """漲跌欄含 <p> 標籤，不得污染數值。"""
    prices = extract_mi_index(mi_index_raw)
    assert all(isinstance(v["chg"], float) for v in prices.values())
