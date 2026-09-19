"""股數 × 收盤價 → 億元，再依板塊加總。"""
from pipeline.extract import is_stock

YI = 1e8  # 1 億元


def to_stock_flows(insti_rows: list[dict], prices: dict[str, dict]) -> dict[str, dict]:
    """個股法人買賣超金額（億元）。

    T86 與 TPEX 給的都是股數，須乘收盤價換算。無收盤價者略過
    （當日停牌等情形），非 4 位數代號（權證）亦排除。
    """
    out = {}
    for row in insti_rows:
        code = row["code"]
        if not is_stock(code):
            continue
        price = prices.get(code)
        if price is None or price["close"] <= 0:
            continue
        close = price["close"]
        net_shares = row["net_shares"]
        foreign_shares = row.get("foreign_shares", 0)
        trust_shares = row.get("trust_shares", 0)
        dealer_shares = row.get("dealer_shares", 0)
        out[code] = {
            "name": row["name"] or price["name"],
            "market": row["market"],
            "net_yi": net_shares * close / YI,
            "foreign_yi": foreign_shares * close / YI,
            "trust_yi": trust_shares * close / YI,
            "dealer_yi": dealer_shares * close / YI,
            "net_shares": net_shares,
            "foreign_shares": foreign_shares,
            "trust_shares": trust_shares,
            "dealer_shares": dealer_shares,
            "close": close,
            "chg": price["chg"],
        }
    return out


def aggregate_sectors(sectors: dict[str, list[str]], flows: dict[str, dict]) -> dict[str, dict]:
    """板塊淨買超 = 成分股金額加總。個股可屬多板塊，各板塊獨立計算。"""
    result = {}
    for name, codes in sectors.items():
        present = [c for c in codes if c in flows]
        result[name] = {
            "net_yi": sum(flows[c]["net_yi"] for c in present),
            "foreign_yi": sum(flows[c].get("foreign_yi", 0) for c in present),
            "trust_yi": sum(flows[c].get("trust_yi", 0) for c in present),
            "dealer_yi": sum(flows[c].get("dealer_yi", 0) for c in present),
            "size": len(present),
            "stocks": present,
        }
    return result
