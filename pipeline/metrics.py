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


def build_metrics(history: list[dict[str, float]]) -> list[dict]:
    """由每日板塊淨買超序列算出完整指標。

    history 依日期由舊到新排序，每元素為 {板塊名: 當日淨買超億元}。
    """
    if not history:
        raise ValueError("history 不得為空，至少需要一個交易日的資料")

    names = sorted({name for day in history for name in day})
    series = {name: [day.get(name, 0.0) for day in history] for name in names}

    rows = []
    for name in names:
        values = series[name]
        net5 = window_sum(values, 5)
        net20 = window_sum(values, 20)
        rows.append(
            {
                "name": name,
                "net_1d_yi": values[-1],
                "net_5d_yi": net5,
                "net_20d_yi": net20,
                "accel": accel(net5, net20),
            }
        )

    max20 = max((abs(r["net_20d_yi"]) for r in rows), default=0.0)
    for row in rows:
        row["radius"] = radius(row["net_20d_yi"], max20)
        row["quadrant"] = quadrant(row["net_5d_yi"], row["accel"])
    return rows
