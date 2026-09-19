def test_t86_shape(t86_raw):
    assert t86_raw["stat"] == "OK"
    assert t86_raw["date"] == "20260916"
    assert len(t86_raw["fields"]) == 19
    assert len(t86_raw["data"]) == 16893


def test_mi_index_has_close_table(mi_index_raw):
    tables = [t for t in mi_index_raw["tables"] if "收盤價" in t.get("fields", [])]
    assert len(tables) == 1
    assert len(tables[0]["fields"]) == 16


def test_tpex_insti_shape(tpex_insti_raw):
    table = tpex_insti_raw["tables"][0]
    assert table["date"] == "115/09/16"
    assert len(table["fields"]) == 24
    assert len(table["data"]) == 886


def test_tpex_otc_shape(tpex_otc_raw):
    table = tpex_otc_raw["tables"][0]
    assert table["date"] == "115/09/16"
    assert len(table["data"]) == 1014


def test_bfi_has_total_row(bfi_raw):
    totals = [r for r in bfi_raw["data"] if r[0].startswith("合計")]
    assert len(totals) == 1
    assert totals[0][3] == "-20,308,782,437"
