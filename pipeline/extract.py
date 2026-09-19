"""四支端點回應 → 正規化資料列。欄位索引見計畫文件，已實測確認。"""
import re

from pipeline.parsers import strip_html, to_number

_STOCK = re.compile(r"^\d{4}$")

# T86 欄位索引
T86_CODE, T86_NAME, T86_NET = 0, 1, 18
# MI_INDEX 欄位索引
MI_CODE, MI_NAME, MI_CLOSE, MI_CHG = 0, 1, 8, 10
# TPEX insti 欄位索引（欄位名七組重複，只能靠索引）
TPEX_CODE, TPEX_NAME, TPEX_NET = 0, 1, 23
# TPEX otc 欄位索引
OTC_CODE, OTC_NAME, OTC_CLOSE, OTC_CHG = 0, 1, 2, 3


def is_stock(code: str) -> bool:
    """恰好 4 位數字才是普通股或 ETF。權證為 6 位，另有 5 位與含英文者。"""
    return bool(_STOCK.match(code.strip()))


def extract_t86(raw: dict) -> list[dict]:
    """上市三大法人買賣超（單位：股數）。不過濾，過濾交由呼叫端決定。"""
    out = []
    for row in raw["data"]:
        out.append(
            {
                "code": row[T86_CODE].strip(),
                "name": strip_html(row[T86_NAME]),
                "net_shares": to_number(row[T86_NET]),
                "market": "TWSE",
            }
        )
    return out


def extract_mi_index(raw: dict) -> dict[str, dict]:
    """上市收盤行情。回應含多張表，取 fields 含「收盤價」的那一張。"""
    tables = [t for t in raw["tables"] if "收盤價" in t.get("fields", [])]
    if len(tables) != 1:
        raise ValueError(f"MI_INDEX 預期 1 張收盤行情表，實得 {len(tables)} 張")
    out = {}
    for row in tables[0]["data"]:
        code = row[MI_CODE].strip()
        out[code] = {
            "name": strip_html(row[MI_NAME]),
            "close": to_number(row[MI_CLOSE]),
            "chg": to_number(row[MI_CHG]),
        }
    return out


def extract_tpex_insti(raw: dict) -> list[dict]:
    """上櫃三大法人買賣超（單位：股數）。"""
    table = raw["tables"][0]
    out = []
    for row in table["data"]:
        out.append(
            {
                "code": row[TPEX_CODE].strip(),
                "name": strip_html(row[TPEX_NAME]),
                "net_shares": to_number(row[TPEX_NET]),
                "market": "TPEX",
            }
        )
    return out


def extract_tpex_otc(raw: dict) -> dict[str, dict]:
    """上櫃收盤行情。此端點已排除權證，筆數遠少於 dailyQuotes。"""
    table = raw["tables"][0]
    out = {}
    for row in table["data"]:
        code = row[OTC_CODE].strip()
        out[code] = {
            "name": strip_html(row[OTC_NAME]),
            "close": to_number(row[OTC_CLOSE]),
            "chg": to_number(row[OTC_CHG]),
        }
    return out
