import pytest

from pipeline.metrics import accel, build_metrics, quadrant, radius, window_sum


def test_window_sum_takes_tail():
    assert window_sum([1, 2, 3, 4, 5], 3) == 12.0      # 3+4+5
    assert window_sum([1, 2], 5) == 3.0                # 不足則全取
    assert window_sum([], 5) == 0.0


def test_accel():
    # net5=10 → 日均 2.0；net20=20 → 日均 1.0；加速度 +1.0
    assert accel(10.0, 20.0) == 1.0
    assert accel(5.0, 20.0) == 0.0
    assert accel(0.0, 20.0) == -1.0


@pytest.mark.parametrize(
    "net5,acc,expected",
    [
        (1.0, 1.0, "surge"),      # 右上：錢在流進而且越流越快
        (1.0, -1.0, "rotation"),  # 右下：還在流進但慢下來了
        (1.0, 0.0, "rotation"),   # accel == 0 歸於輪動
        (-1.0, 1.0, "watch"),     # 左上：流出但在減緩
        (-1.0, -1.0, "ebb"),      # 左下：退潮
        (0.0, 1.0, "watch"),      # net5 == 0 歸於觀察側
        (0.0, -1.0, "ebb"),
    ],
)
def test_quadrant(net5, acc, expected):
    assert quadrant(net5, acc) == expected


def test_radius_bounds():
    assert radius(0.0, 100.0) == 22.0
    assert radius(100.0, 100.0) == 55.0
    assert radius(-100.0, 100.0) == 55.0        # 取絕對值
    assert 22.0 < radius(50.0, 100.0) < 55.0


def test_radius_handles_zero_max():
    assert radius(0.0, 0.0) == 22.0


def test_build_metrics_basic():
    history = [{"A": 1.0, "B": -1.0} for _ in range(20)]
    out = {m["name"]: m for m in build_metrics(history)}
    assert out["A"]["net_5d_yi"] == 5.0
    assert out["A"]["net_20d_yi"] == 20.0
    assert out["A"]["net_1d_yi"] == 1.0
    assert out["A"]["accel"] == 0.0
    assert out["A"]["quadrant"] == "rotation"
    assert out["B"]["quadrant"] == "ebb"


def test_build_metrics_radius_relative_to_max():
    history = [{"大": 10.0, "小": 1.0} for _ in range(20)]
    out = {m["name"]: m for m in build_metrics(history)}
    assert out["大"]["radius"] == 55.0
    assert out["小"]["radius"] < 55.0


def test_build_metrics_requires_history():
    with pytest.raises(ValueError):
        build_metrics([])


def test_compute_stock_metrics_and_radar():
    from pipeline.metrics import compute_stock_metrics, build_radar
    
    # 建立 5 天歷史，每天為 {code: item}
    history = [
        {
            "2330": {
                "code": "2330", "name": "台積電", "market": "TWSE", "close": 1000.0, "chg": 10.0,
                "foreign_shares": 10000, "trust_shares": 5000, "dealer_shares": 1000, "net_shares": 16000,
                "foreign_yi": 1.0, "trust_yi": 0.5, "dealer_yi": 0.1, "net_yi": 1.6
            },
            "2317": {
                "code": "2317", "name": "鴻海", "market": "TWSE", "close": 200.0, "chg": -2.0,
                "foreign_shares": -10000, "trust_shares": -5000, "dealer_shares": -1000, "net_shares": -16000,
                "foreign_yi": -0.2, "trust_yi": -0.1, "dealer_yi": -0.02, "net_yi": -0.32
            },
            "2454": {
                "code": "2454", "name": "聯發科", "market": "TWSE", "close": 1200.0, "chg": 5.0,
                "foreign_shares": 5000, "trust_shares": -2000, "dealer_shares": 0, "net_shares": 3000,
                "foreign_yi": 0.6, "trust_yi": -0.24, "dealer_yi": 0.0, "net_yi": 0.36
            }
        }
        for _ in range(5)
    ]
    
    stk_metrics = compute_stock_metrics(history)
    assert "2330" in stk_metrics
    tsmc = stk_metrics["2330"]
    assert tsmc["foreign_streak"] == 5
    assert tsmc["trust_streak"] == 5
    assert tsmc["cost_20d"] == 1000.0
    assert tsmc["diff_pct"] == 0.0
    
    radar = build_radar(history[-1], stk_metrics)
    assert any(s["code"] == "2330" for s in radar["co_buy"])
    assert any(s["code"] == "2317" for s in radar["co_sell"])
    assert any(s["code"] == "2454" for s in radar["divergence"])
    assert len(radar["foreign_streak_top"]) >= 1

