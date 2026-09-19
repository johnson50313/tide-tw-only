"""BFI82U 對帳。以收盤價回推整日成交本身即有誤差，此為量級健檢而非精確比對。

結構正確性由 extract 的欄位恆等式測試保證，兩者互補。
"""
from pipeline.extract import extract_mi_index, extract_t86
from pipeline.parsers import to_number

TOLERANCE = 0.005  # 實測 5 個交易日誤差率 0.023%~0.366%，0.5% 留足餘裕


def _bfi_total(bfi_raw: dict) -> tuple[float, float]:
    """回傳（合計買賣差額, 合計成交總額）。"""
    rows = [r for r in bfi_raw["data"] if r[0].strip().startswith("合計")]
    if len(rows) != 1:
        raise ValueError(f"BFI82U 預期 1 列合計，實得 {len(rows)} 列")
    row = rows[0]
    return to_number(row[3]), to_number(row[1]) + to_number(row[2])


def reconcile(t86_raw: dict, mi_raw: dict, bfi_raw: dict) -> dict:
    """比對逐檔回推總額與官方公布總額。

    須使用 T86 全體證券（含權證）：BFI82U 統計範圍涵蓋整個集中市場。
    分母用成交總額而非淨額，避免淨額趨近零時相對誤差爆增。
    """
    prices = extract_mi_index(mi_raw)
    computed = 0.0
    for row in extract_t86(t86_raw):
        price = prices.get(row["code"])
        if price:
            computed += row["net_shares"] * price["close"]

    reference, turnover = _bfi_total(bfi_raw)
    error_ratio = abs(computed - reference) / turnover if turnover else float("inf")
    return {
        "computed": computed,
        "reference": reference,
        "turnover": turnover,
        "error_ratio": error_ratio,
        "passed": error_ratio < TOLERANCE,
    }
