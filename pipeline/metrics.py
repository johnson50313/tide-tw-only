"""泡泡圖指標。定義取自原站公開前端程式碼，見規格第 5 節。

X 軸為近 5 日淨買超，Y 軸為買超加速度（近 5 日日均減近 20 日日均），
泡泡大小反映近 20 日淨買超的絕對值。
"""
R_MIN, R_MAX = 22.0, 55.0
R_SPAN = R_MAX - R_MIN


def window_sum(values: list[float], n: int) -> float:
    """取序列末端 n 個值加總。序列依日期由舊到新排序，末端即最近幾日。"""
    if not values:
        return 0.0
    return float(sum(values[-n:]))


def accel(net5: float, net20: float) -> float:
    """買超加速度：近 5 日日均減近 20 日日均。正值代表買超在加速。"""
    return net5 / 5 - net20 / 20


def quadrant(net5: float, acc: float) -> str:
    """四象限分類。"""
    if net5 > 0 and acc > 0:
        return "surge"      # 漲潮：錢在流進而且越流越快
    if net5 > 0:
        return "rotation"   # 輪動：還在流進但慢下來了
    if acc > 0:
        return "watch"      # 觀察：流出但在減緩
    return "ebb"            # 退潮


def radius(net20: float, max20: float) -> float:
    """泡泡半徑，依近 20 日淨買超絕對值相對全體最大值線性映射。"""
    if max20 <= 0:
        return R_MIN
    return max(R_MIN, min(R_MAX, R_MIN + abs(net20) / max20 * R_SPAN))


def compute_stock_metrics(history_flows: list[dict[str, dict]]) -> dict[str, dict]:
    """計算每檔個股的 5日/20日分項累計、20日法人成本均價、外資與投信連買連賣天數。

    history_flows: 由舊到新排序，每筆為 {code: flow_dict}。
    """
    if not history_flows:
        return {}

    latest = history_flows[-1]
    results = {}

    for code, item in latest.items():
        # 收集該檔個股在歷史中的序列
        series = [day[code] for day in history_flows if code in day]
        if not series:
            continue

        latest_close = item["close"]

        # 1. 計算外資、投信、自營商 5日與 20日累計
        f_1d = item.get("foreign_yi", 0.0)
        t_1d = item.get("trust_yi", 0.0)
        d_1d = item.get("dealer_yi", 0.0)

        f_5d = sum(d.get("foreign_yi", 0.0) for d in series[-5:])
        t_5d = sum(d.get("trust_yi", 0.0) for d in series[-5:])
        d_5d = sum(d.get("dealer_yi", 0.0) for d in series[-5:])

        f_20d = sum(d.get("foreign_yi", 0.0) for d in series[-20:])
        t_20d = sum(d.get("trust_yi", 0.0) for d in series[-20:])
        d_20d = sum(d.get("dealer_yi", 0.0) for d in series[-20:])

        net_5d = sum(d.get("net_yi", 0.0) for d in series[-5:])
        net_20d = sum(d.get("net_yi", 0.0) for d in series[-20:])

        # 2. 計算 20 日法人買進加權平均成本 (VWAP)
        # 取近 20 日法人淨買超 > 0 之日進行加權成本計算
        pos_shares = 0.0
        pos_cost_sum = 0.0
        for d in series[-20:]:
            net_s = d.get("net_shares", 0.0)
            c = d.get("close", 0.0)
            if net_s > 0 and c > 0:
                pos_shares += net_s
                pos_cost_sum += net_s * c

        cost_20d = round(pos_cost_sum / pos_shares, 2) if pos_shares > 0 else None
        diff_pct = (
            round(((latest_close - cost_20d) / cost_20d) * 100, 2)
            if cost_20d and cost_20d > 0
            else None
        )

        # 3. 計算外資與投信連續買賣天數 (Streak)
        # 從最新一天往前數
        foreign_streak = 0
        trust_streak = 0

        # 外資連買/連賣
        if len(series) > 0:
            first_sign = 1 if series[-1].get("foreign_shares", 0) > 0 else (-1 if series[-1].get("foreign_shares", 0) < 0 else 0)
            if first_sign != 0:
                for d in reversed(series):
                    s = 1 if d.get("foreign_shares", 0) > 0 else (-1 if d.get("foreign_shares", 0) < 0 else 0)
                    if s == first_sign:
                        foreign_streak += first_sign
                    else:
                        break

        # 投信連買/連賣
        if len(series) > 0:
            first_t_sign = 1 if series[-1].get("trust_shares", 0) > 0 else (-1 if series[-1].get("trust_shares", 0) < 0 else 0)
            if first_t_sign != 0:
                for d in reversed(series):
                    s = 1 if d.get("trust_shares", 0) > 0 else (-1 if d.get("trust_shares", 0) < 0 else 0)
                    if s == first_t_sign:
                        trust_streak += first_t_sign
                    else:
                        break

        results[code] = {
            "net_5d_yi": round(net_5d, 4),
            "net_20d_yi": round(net_20d, 4),
            "foreign_1d_yi": round(f_1d, 4),
            "trust_1d_yi": round(t_1d, 4),
            "dealer_1d_yi": round(d_1d, 4),
            "foreign_5d_yi": round(f_5d, 4),
            "trust_5d_yi": round(t_5d, 4),
            "dealer_5d_yi": round(d_5d, 4),
            "foreign_20d_yi": round(f_20d, 4),
            "trust_20d_yi": round(t_20d, 4),
            "dealer_20d_yi": round(d_20d, 4),
            "cost_20d": cost_20d,
            "diff_pct": diff_pct,
            "foreign_streak": foreign_streak,
            "trust_streak": trust_streak,
        }

    return results


def build_radar(latest_flows: dict[str, dict], stock_metrics: dict[str, dict]) -> dict:
    """產出進階籌碼雷達榜單（土洋同買、土洋同賣、土洋對作、外資連買、投信連買）。"""
    items = []
    for code, flow in latest_flows.items():
        m = stock_metrics.get(code, {})
        items.append({
            "code": code,
            "name": flow["name"],
            "market": flow["market"],
            "close": flow["close"],
            "chg": flow["chg"],
            "net_1d_yi": round(flow["net_yi"], 4),
            "foreign_1d_yi": round(flow.get("foreign_yi", 0.0), 4),
            "trust_1d_yi": round(flow.get("trust_yi", 0.0), 4),
            "dealer_1d_yi": round(flow.get("dealer_yi", 0.0), 4),
            "net_5d_yi": m.get("net_5d_yi", 0.0),
            "foreign_5d_yi": m.get("foreign_5d_yi", 0.0),
            "trust_5d_yi": m.get("trust_5d_yi", 0.0),
            "cost_20d": m.get("cost_20d"),
            "diff_pct": m.get("diff_pct"),
            "foreign_streak": m.get("foreign_streak", 0),
            "trust_streak": m.get("trust_streak", 0),
        })

    # 1. 土洋同買（外資與投信皆大買 >= 0.05 億，按合計降序）
    co_buy = [
        item for item in items
        if item["foreign_1d_yi"] >= 0.05 and item["trust_1d_yi"] >= 0.05
    ]
    co_buy.sort(key=lambda x: (x["foreign_1d_yi"] + x["trust_1d_yi"]), reverse=True)

    # 2. 土洋同賣（外資與投信皆賣超 <= -0.05 億，按合計升序）
    co_sell = [
        item for item in items
        if item["foreign_1d_yi"] <= -0.05 and item["trust_1d_yi"] <= -0.05
    ]
    co_sell.sort(key=lambda x: (x["foreign_1d_yi"] + x["trust_1d_yi"]))

    # 3. 土洋對作（外資買投信賣，或投信買外資賣，分歧 >= 0.1 億）
    divergence = [
        item for item in items
        if (item["foreign_1d_yi"] >= 0.1 and item["trust_1d_yi"] <= -0.05)
        or (item["trust_1d_yi"] >= 0.1 and item["foreign_1d_yi"] <= -0.05)
    ]
    divergence.sort(key=lambda x: abs(x["foreign_1d_yi"] - x["trust_1d_yi"]), reverse=True)

    # 4. 外資連買榜 (streak >= 3)
    foreign_streak_top = [
        item for item in items
        if item["foreign_streak"] >= 3
    ]
    foreign_streak_top.sort(key=lambda x: (x["foreign_streak"], x["foreign_5d_yi"]), reverse=True)

    # 5. 投信連買榜 (streak >= 3)
    trust_streak_top = [
        item for item in items
        if item["trust_streak"] >= 3
    ]
    trust_streak_top.sort(key=lambda x: (x["trust_streak"], x["trust_5d_yi"]), reverse=True)

    return {
        "co_buy": co_buy[:30],
        "co_sell": co_sell[:30],
        "divergence": divergence[:30],
        "foreign_streak_top": foreign_streak_top[:30],
        "trust_streak_top": trust_streak_top[:30],
    }


def build_metrics(
    history: list[dict[str, float]],
    foreign_history: list[dict[str, float]] | None = None,
    trust_history: list[dict[str, float]] | None = None,
    dealer_history: list[dict[str, float]] | None = None,
) -> list[dict]:
    """由每日板塊淨買超序列算出完整指標。

    history 依日期由舊到新排序，每元素為 {板塊名: 當日淨買超億元}。
    """
    if not history:
        raise ValueError("history 不得為空，至少需要一個交易日的資料")

    names = sorted({name for day in history for name in day})
    series = {name: [day.get(name, 0.0) for day in history] for name in names}

    f_series = {name: [day.get(name, 0.0) for day in (foreign_history or [])] for name in names}
    t_series = {name: [day.get(name, 0.0) for day in (trust_history or [])] for name in names}
    d_series = {name: [day.get(name, 0.0) for day in (dealer_history or [])] for name in names}

    rows = []
    for name in names:
        values = series[name]
        net5 = window_sum(values, 5)
        net20 = window_sum(values, 20)

        f_vals = f_series.get(name, [])
        t_vals = t_series.get(name, [])
        d_vals = d_series.get(name, [])

        rows.append(
            {
                "name": name,
                "net_1d_yi": values[-1] if values else 0.0,
                "net_5d_yi": net5,
                "net_20d_yi": net20,
                "foreign_1d_yi": f_vals[-1] if f_vals else 0.0,
                "foreign_5d_yi": window_sum(f_vals, 5),
                "foreign_20d_yi": window_sum(f_vals, 20),
                "trust_1d_yi": t_vals[-1] if t_vals else 0.0,
                "trust_5d_yi": window_sum(t_vals, 5),
                "trust_20d_yi": window_sum(t_vals, 20),
                "dealer_1d_yi": d_vals[-1] if d_vals else 0.0,
                "dealer_5d_yi": window_sum(d_vals, 5),
                "dealer_20d_yi": window_sum(d_vals, 20),
                "accel": accel(net5, net20),
            }
        )

    max20 = max((abs(r["net_20d_yi"]) for r in rows), default=0.0)
    for row in rows:
        row["radius"] = radius(row["net_20d_yi"], max20)
        row["quadrant"] = quadrant(row["net_5d_yi"], row["accel"])
    return rows
