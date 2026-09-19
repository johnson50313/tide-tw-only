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
