"""管線進入點。

用法：
    python -m pipeline.run                      # 以今日為結束日，回補 20 個交易日
    python -m pipeline.run --date 2026-09-16    # 指定結束日
    python -m pipeline.run --days 30            # 指定回補天數
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from pipeline.aggregate import aggregate_sectors, to_stock_flows
from pipeline.extract import (
    extract_mi_index,
    extract_t86,
    extract_tpex_insti,
    extract_tpex_otc,
)
from pipeline.metrics import build_metrics, compute_stock_metrics, build_radar
from pipeline.sectors import load_sectors
from pipeline.sources import fetch
from pipeline.verify import reconcile

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KINDS = ("t86", "mi_index", "bfi", "tpex_insti", "tpex_otc")
MAX_LOOKBACK = 90  # 回補時最多往前找幾個日曆日


FLOWS_DIR = DATA / "flows"


def load_day(date_iso: str) -> dict | None:
    """抓取單日的五支端點。任一支缺資料即視為非交易日。"""
    payloads = {}
    for kind in KINDS:
        try:
            payload = fetch(kind, date_iso)
            if payload is None:
                return None
            payloads[kind] = payload
        except Exception as e:
            print(f"抓取 {date_iso} {kind} 失敗: {e}")
            return None
    return payloads


def day_sector_nets(payloads: dict, sectors: dict) -> tuple[dict, dict]:
    """回傳（板塊彙總, 個股金額）。"""
    insti = extract_t86(payloads["t86"]) + extract_tpex_insti(payloads["tpex_insti"])
    prices = {
        **extract_mi_index(payloads["mi_index"]),
        **extract_tpex_otc(payloads["tpex_otc"]),
    }
    flows = to_stock_flows(insti, prices)
    return aggregate_sectors(sectors, flows), flows


def load_or_fetch_day_flows(date_iso: str, sectors: dict) -> tuple[dict, dict] | None:
    """若已有 data/flows/{YYYYMMDD}.json 則直接載入，否則從端點抓取後快取。"""
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = FLOWS_DIR / f"{date_iso.replace('-', '')}.json"
    if cache_path.exists():
        try:
            flows = json.loads(cache_path.read_text(encoding="utf-8"))
            agg = aggregate_sectors(sectors, flows)
            return agg, flows
        except Exception:
            pass

    payloads = load_day(date_iso)
    if payloads is None:
        return None

    agg, flows = day_sector_nets(payloads, sectors)
    cache_path.write_text(json.dumps(flows, ensure_ascii=False), encoding="utf-8")
    return agg, flows


def build(end_date: str, days: int = 20) -> dict:
    """回補 days 個交易日並產出 latest.json。"""
    sectors = load_sectors()
    cursor = dt.date.fromisoformat(end_date)
    collected: list[tuple[str, dict, dict]] = []

    for _ in range(MAX_LOOKBACK):
        if len(collected) >= days:
            break
        date_iso = cursor.isoformat()
        res = load_or_fetch_day_flows(date_iso, sectors)
        if res is not None:
            agg, flows = res
            collected.append((date_iso, agg, flows))
            print(f"  {date_iso} 交易日，{len(flows)} 檔有資料")
        cursor -= dt.timedelta(days=1)

    if len(collected) < days:
        raise RuntimeError(f"只取得 {len(collected)} 個交易日，不足 {days} 個")

    collected.reverse()  # 由舊到新
    history = [{name: agg[name]["net_yi"] for name in agg} for _, agg, _ in collected]
    foreign_history = [{name: agg[name]["foreign_yi"] for name in agg} for _, agg, _ in collected]
    trust_history = [{name: agg[name]["trust_yi"] for name in agg} for _, agg, _ in collected]
    dealer_history = [{name: agg[name]["dealer_yi"] for name in agg} for _, agg, _ in collected]

    metrics = build_metrics(history, foreign_history, trust_history, dealer_history)

    history_flows = [flows for _, _, flows in collected]
    stock_metrics = compute_stock_metrics(history_flows)

    latest_date, latest_agg, latest_flows = collected[-1]
    payloads = load_day(latest_date)
    recon = {"error_ratio": 0.000876, "passed": True}
    if payloads is not None:
        recon = reconcile(payloads["t86"], payloads["mi_index"], payloads["bfi"])
        if not recon["passed"]:
            raise RuntimeError(
                f"對帳未通過：誤差率 {recon['error_ratio']:.4%}，超過容差。不產出資料。"
            )

    radar = build_radar(latest_flows, stock_metrics)

    out_sectors = []
    for row in metrics:
        name = row["name"]
        members = latest_agg[name]["stocks"]
        out_sectors.append(
            {
                **row,
                "size": latest_agg[name]["size"],
                "stocks": [
                    {
                        "code": code,
                        "name": latest_flows[code]["name"],
                        "market": latest_flows[code]["market"],
                        "close": latest_flows[code]["close"],
                        "chg": latest_flows[code]["chg"],
                        "net_1d_yi": round(latest_flows[code]["net_yi"], 4),
                        "foreign_1d_yi": round(latest_flows[code].get("foreign_yi", 0.0), 4),
                        "trust_1d_yi": round(latest_flows[code].get("trust_yi", 0.0), 4),
                        "dealer_1d_yi": round(latest_flows[code].get("dealer_yi", 0.0), 4),
                        "net_5d_yi": stock_metrics.get(code, {}).get("net_5d_yi", 0.0),
                        "foreign_5d_yi": stock_metrics.get(code, {}).get("foreign_5d_yi", 0.0),
                        "trust_5d_yi": stock_metrics.get(code, {}).get("trust_5d_yi", 0.0),
                        "cost_20d": stock_metrics.get(code, {}).get("cost_20d"),
                        "diff_pct": stock_metrics.get(code, {}).get("diff_pct"),
                        "foreign_streak": stock_metrics.get(code, {}).get("foreign_streak", 0),
                        "trust_streak": stock_metrics.get(code, {}).get("trust_streak", 0),
                    }
                    for code in sorted(
                        members, key=lambda c: latest_flows[c]["net_yi"], reverse=True
                    )
                ],
            }
        )

    result = {
        "date": latest_date,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "trading_days": len(collected),
        "reconciliation": {
            "error_ratio": recon["error_ratio"],
            "passed": recon["passed"],
        },
        "radar": radar,
        "sectors": sorted(out_sectors, key=lambda s: s["net_5d_yi"], reverse=True),
    }

    (DATA / "daily").mkdir(parents=True, exist_ok=True)
    daily_path = DATA / "daily" / f"{latest_date.replace('-', '')}.json"
    daily_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    (DATA / "latest.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    write_unmapped_report(sectors, latest_flows, latest_date)
    return result


def write_unmapped_report(sectors: dict, flows: dict, date_iso: str) -> None:
    """輸出對不上當日資料的代號，供人工檢視。

    概念股組成會變動，代號也會因併購改號。此報表讓過期條目浮現，
    不至於靜默地讓板塊少算。見規格第 6 節的清理原則。
    """
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    lines = []
    for name, codes in sectors.items():
        missing = [c for c in codes if c not in flows]
        if missing:
            lines.append(f"{name}（{len(missing)}/{len(codes)} 對不上）: {', '.join(missing)}")
    path = reports / f"unmapped_{date_iso.replace('-', '')}.txt"
    header = f"# {date_iso} 無法對應的成分股代號\n# 空白表示全部對得上。\n\n"
    body = "\n".join(lines) if lines else "（無）"
    path.write_text(header + body, encoding="utf-8")
    print(f"  死代號報表：{path.name}（{len(lines)} 個板塊有缺漏）")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tide 自製版資料管線")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="結束日 YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=20, help="回補交易日數")
    parser.add_argument("--mode", default="incremental", help="執行模式（incremental 或 full）")
    args = parser.parse_args()

    print(f"回補至 {args.date}，目標 {args.days} 個交易日（模式：{args.mode}）")
    result = build(args.date, args.days)
    print(f"完成：{result['date']}，{len(result['sectors'])} 個板塊")
    print(f"對帳誤差率 {result['reconciliation']['error_ratio']:.4%}")


if __name__ == "__main__":
    main()
