from pipeline.verify import TOLERANCE, reconcile


def test_reconcile_passes_on_real_data(t86_raw, mi_index_raw, bfi_raw):
    result = reconcile(t86_raw, mi_index_raw, bfi_raw)
    assert result["reference"] == -20308782437.0
    assert result["turnover"] == 323327481545.0 + 343636263982.0
    # 實測 2026-09-16 誤差率 0.023%
    assert result["error_ratio"] < 0.001
    assert result["passed"] is True


def test_reconcile_uses_all_securities(t86_raw, mi_index_raw, bfi_raw):
    """若誤用 4 位數過濾，誤差率會是 2% 以上（實測淨額分母下達 77%）。

    此測試確保 computed 接近 reference 而非遠小於它。
    """
    result = reconcile(t86_raw, mi_index_raw, bfi_raw)
    assert abs(result["computed"]) > abs(result["reference"]) * 0.9


def test_tolerance_value():
    assert TOLERANCE == 0.005
