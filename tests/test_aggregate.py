from pipeline.aggregate import YI, aggregate_sectors, to_stock_flows


def test_yi_constant():
    assert YI == 1e8


def test_to_stock_flows_converts_to_yi():
    insti = [{"code": "2330", "name": "台積電", "net_shares": 1_000_000.0, "market": "TWSE"}]
    prices = {"2330": {"name": "台積電", "close": 1000.0, "chg": 5.0}}
    flows = to_stock_flows(insti, prices)
    # 100 萬股 × 1000 元 = 10 億元
    assert flows["2330"]["net_yi"] == 10.0
    assert flows["2330"]["close"] == 1000.0
    assert flows["2330"]["chg"] == 5.0
    assert flows["2330"]["market"] == "TWSE"


def test_to_stock_flows_filters_non_stock():
    insti = [
        {"code": "2330", "name": "台積電", "net_shares": 1000.0, "market": "TWSE"},
        {"code": "031234", "name": "某權證", "net_shares": 9e9, "market": "TWSE"},
    ]
    prices = {"2330": {"name": "台積電", "close": 100.0, "chg": 0.0},
              "031234": {"name": "某權證", "close": 1.0, "chg": 0.0}}
    flows = to_stock_flows(insti, prices)
    assert set(flows) == {"2330"}


def test_to_stock_flows_skips_missing_price():
    insti = [{"code": "9999", "name": "無價股", "net_shares": 1000.0, "market": "TWSE"}]
    flows = to_stock_flows(insti, {})
    assert flows == {}


def test_aggregate_sectors_sums_members():
    sectors = {"測試板塊": ["1111", "2222"], "另一板塊": ["2222"]}
    flows = {
        "1111": {"name": "A", "market": "TWSE", "net_yi": 3.0, "close": 10.0, "chg": 0.0},
        "2222": {"name": "B", "market": "TPEX", "net_yi": -1.0, "close": 20.0, "chg": 0.0},
    }
    result = aggregate_sectors(sectors, flows)
    assert result["測試板塊"]["net_yi"] == 2.0
    assert result["測試板塊"]["size"] == 2
    assert result["另一板塊"]["net_yi"] == -1.0
    assert result["另一板塊"]["size"] == 1


def test_aggregate_sectors_ignores_absent_members():
    """成分股當日無資料時不計入 size，板塊仍存在。"""
    sectors = {"測試板塊": ["1111", "8888"]}
    flows = {"1111": {"name": "A", "market": "TWSE", "net_yi": 5.0, "close": 1.0, "chg": 0.0}}
    result = aggregate_sectors(sectors, flows)
    assert result["測試板塊"]["net_yi"] == 5.0
    assert result["測試板塊"]["size"] == 1
    assert result["測試板塊"]["stocks"] == ["1111"]


def test_real_data_end_to_end(t86_raw, mi_index_raw, tpex_insti_raw, tpex_otc_raw):
    """以真實樣本跑一遍，確認 76 板塊都算得出數字。"""
    from pipeline.extract import (
        extract_mi_index,
        extract_t86,
        extract_tpex_insti,
        extract_tpex_otc,
    )
    from pipeline.sectors import load_sectors

    insti = extract_t86(t86_raw) + extract_tpex_insti(tpex_insti_raw)
    prices = {**extract_mi_index(mi_index_raw), **extract_tpex_otc(tpex_otc_raw)}
    flows = to_stock_flows(insti, prices)
    sectors = load_sectors()
    result = aggregate_sectors(sectors, flows)
    assert len(result) == 76
    assert all(r["size"] > 0 for r in result.values()), "有板塊一檔都對不上"
    # 601 檔成分股絕大多數有法人交易（允許部分上櫃冷門股當日無法人進出）
    covered = len({c for r in result.values() for c in r["stocks"]})
    assert covered >= 580, f"只對上 {covered} 檔"
