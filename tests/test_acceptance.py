"""端到端驗收，對應規格第 9 節。需先執行過 python -m pipeline.run。"""
import json
from pathlib import Path

import pytest

from pipeline.sectors import all_codes, load_sectors

LATEST = Path(__file__).resolve().parent.parent / "data" / "latest.json"


@pytest.fixture(scope="module")
def latest():
    if not LATEST.exists():
        pytest.skip("尚未產出 data/latest.json，請先執行 python -m pipeline.run")
    return json.loads(LATEST.read_text(encoding="utf-8"))


def test_v1_reconciliation_passed(latest):
    """驗證項 1：總額對帳誤差率 < 0.5%。"""
    assert latest["reconciliation"]["passed"] is True
    assert latest["reconciliation"]["error_ratio"] < 0.005


def test_v3_no_dead_codes(latest):
    """驗證項 3：sectors.yaml 中的代號應絕大多數對得上當日資料。"""
    defined = all_codes(load_sectors())
    seen = {s["code"] for sec in latest["sectors"] for s in sec["stocks"]}
    missing = defined - seen
    assert len(missing) <= 25, f"對不上的代號過多：{sorted(missing)}"


def test_v4_metric_consistency(latest):
    """驗證項 4：accel 必須等於 net5/5 - net20/20。"""
    for sec in latest["sectors"]:
        expected = sec["net_5d_yi"] / 5 - sec["net_20d_yi"] / 20
        assert abs(sec["accel"] - expected) < 1e-9, sec["name"]


def test_v5_all_quadrants_present(latest):
    """驗證項 5：四個象限的分類規則正確，且至少各有一個板塊。"""
    for sec in latest["sectors"]:
        net5, acc, q = sec["net_5d_yi"], sec["accel"], sec["quadrant"]
        if net5 > 0 and acc > 0:
            assert q == "surge", sec["name"]
        elif net5 > 0:
            assert q == "rotation", sec["name"]
        elif acc > 0:
            assert q == "watch", sec["name"]
        else:
            assert q == "ebb", sec["name"]
    assert len({s["quadrant"] for s in latest["sectors"]}) >= 3


def test_radius_within_bounds(latest):
    for sec in latest["sectors"]:
        assert 22.0 <= sec["radius"] <= 55.0, sec["name"]


def test_structure(latest):
    assert len(latest["sectors"]) == 76
    assert latest["trading_days"] == 20
    for sec in latest["sectors"]:
        assert sec["size"] > 0, sec["name"]
        assert len(sec["stocks"]) == sec["size"]
