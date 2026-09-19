"""下載五支端點的真實回應，存為測試樣本。只需執行一次。"""
import json
import time
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
DATE_TWSE = "20260916"
DATE_TPEX = "2026/09/16"

TARGETS = {
    "t86": f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={DATE_TWSE}&selectType=ALL",
    "mi_index": f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&date={DATE_TWSE}&type=ALL",
    "bfi": f"https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json&dayDate={DATE_TWSE}&type=day",
    "tpex_insti": f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?type=Daily&sect=EW&date={DATE_TPEX}&response=json",
    "tpex_otc": f"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={DATE_TPEX}&type=EW&response=json",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.tpex.org.tw/",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in TARGETS.items():
        resp = requests.get(url, headers=HEADERS, timeout=40)
        resp.raise_for_status()
        payload = resp.json()
        path = OUT / f"{name}_20260916.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(f"{name}: {path.stat().st_size:,} bytes")
        time.sleep(2)


if __name__ == "__main__":
    main()
