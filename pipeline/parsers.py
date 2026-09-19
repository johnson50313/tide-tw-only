"""交易所回應的解析工具。四支端點格式各異，共用的正規化集中於此。"""
import re

_TAG = re.compile(r"<[^>]+>")
_EMPTY = {"", "--", "---", "X", "N/A"}


def strip_html(value: str) -> str:
    """剝除 HTML 標籤並去除前後空白。

    TPEX 欄位名含 <br>，MI_INDEX 的漲跌欄是 <p style= color:red>+</p>。
    """
    return _TAG.sub("", str(value)).strip()


def to_number(value) -> float:
    """千分位、正負號、空值標記一律吃下。無法解析時回 0.0。"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = strip_html(value).replace(",", "").replace("+", "")
    if text in _EMPTY:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def roc_to_iso(value: str) -> str:
    """民國年轉西元。"115/09/16" -> "2026-09-16"。"""
    year, month, day = strip_html(value).split("/")
    return f"{int(year) + 1911:04d}-{int(month):02d}-{int(day):02d}"


def iso_to_twse(value: str) -> str:
    """"2026-09-16" -> "20260916"。"""
    return value.replace("-", "")


def iso_to_tpex(value: str) -> str:
    """"2026-09-16" -> "2026/09/16"。"""
    return value.replace("-", "/")
