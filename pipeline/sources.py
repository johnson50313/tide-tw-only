"""端點 URL 組裝、抓取與快取。

TWSE 用西元 YYYYMMDD，TPEX 用西元 YYYY/MM/DD。
非交易日兩者皆回空表而非錯誤，由 is_empty 判別。
"""
import json
import time
from pathlib import Path

import requests

from pipeline.parsers import iso_to_tpex, iso_to_twse

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.tpex.org.tw/"}
REQUEST_GAP = 2.0

_TEMPLATES = {
    "t86": "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={twse}&selectType=ALL",
    "mi_index": "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&date={twse}&type=ALL",
    "bfi": "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json&dayDate={twse}&type=day",
    "tpex_insti": "https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?type=Daily&sect=EW&date={tpex}&response=json",
    "tpex_otc": "https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={tpex}&type=EW&response=json",
}


def build_url(kind: str, date_iso: str) -> str:
    """組裝端點網址。未知 kind 直接 KeyError，不要靜默回退。"""
    template = _TEMPLATES[kind]
    return template.format(twse=iso_to_twse(date_iso), tpex=iso_to_tpex(date_iso))


def is_empty(kind: str, payload: dict) -> bool:
    """非交易日回空表。

    TWSE t86/bfi 為 data 空陣列或 stat 不為 OK；
    TWSE mi_index 為 tables 空或無收盤價表；
    TPEX 為 tables 空或其 data 空。
    """
    stat = str(payload.get("stat", "")).upper()
    if stat and stat != "OK":
        return True

    if kind == "mi_index":
        tables = [t for t in payload.get("tables", []) if "收盤價" in t.get("fields", [])]
        return not tables or not tables[0].get("data")

    if kind.startswith("tpex"):
        tables = payload.get("tables") or []
        return not tables or not tables[0].get("data")

    return not payload.get("data")


def fetch(kind: str, date_iso: str, use_cache: bool = True) -> dict | None:
    """抓取單一端點。回 None 表示該日非交易日。

    原始回應寫入 data/raw/{kind}/{YYYYMMDD}.json，重跑直接讀檔。
    """
    cache = RAW_DIR / kind / f"{iso_to_twse(date_iso)}.json"
    if use_cache and cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
    else:
        url = build_url(kind, date_iso)
        last_err = None
        payload = None
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
                if resp.status_code == 200:
                    payload = resp.json()
                    break
                elif resp.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                else:
                    resp.raise_for_status()
            except Exception as e:
                last_err = e
                time.sleep(2 * (attempt + 1))
        if payload is None:
            if last_err:
                raise last_err
            return None

        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        time.sleep(REQUEST_GAP)
    return None if is_empty(kind, payload) else payload
