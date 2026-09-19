# Tide 潮汐自製版 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一套本機執行的台股法人資金流工具，每個交易日彙整三大法人在 76 個主題板塊的進出，以四象限泡泡圖呈現板塊輪動。

**Architecture:** Python 資料管線（抓取 → 快取 → 清洗 → 換算 → 彙總 → 計算 → 輸出 JSON）搭配零後端的純靜態前端（vanilla JS + 手刻 SVG）。管線與前端唯一介面是 `data/latest.json`。管線手動觸發，前端直接開啟檔案即可。

**Tech Stack:** Python 3.12.7、pytest 8.3.3、PyYAML 6.0.3、requests 2.32.3（皆已安裝，無須新增相依）。前端無任何框架或函式庫。

**Spec:** `docs/superpowers/specs/2026-09-17-tide-clone-design.md`

## Global Constraints

- Python 3.12；僅使用 `requests`、`PyYAML`、標準函式庫。**不得新增其他第三方相依**。
- 金額單位一律為**億元**（1 億 = 1e8 元），欄位名後綴 `_yi`。
- 股票代號一律為**字串**，不得轉成整數（會掉前導零）。
- 所有對交易所的請求須帶 `User-Agent: Mozilla/5.0`；TPEX 另須帶 `Referer: https://www.tpex.org.tw/`。
- 連續請求之間 `time.sleep(2)`。
- 任一端點失敗則該日整體失敗，**保留既有輸出，不得產出部分資料**。
- 日期格式：TWSE 用 `YYYYMMDD`，TPEX 用 `YYYY/MM/DD`（皆為西元；TPEX 回應中的 `date` 欄為民國年）。
- 程式碼註解與使用者訊息用繁體中文。

---

## File Structure

| 檔案 | 責任 |
|---|---|
| `pipeline/parsers.py` | 數值／日期／HTML 正規化工具 |
| `pipeline/sources.py` | 端點 URL 組裝、HTTP 抓取、`data/raw/` 快取 |
| `pipeline/extract.py` | 四支端點回應 → 正規化資料列 |
| `pipeline/sectors.py` | 載入並驗證 `sectors.yaml` |
| `pipeline/aggregate.py` | 股數×價格 → 個股金額 → 板塊彙總 |
| `pipeline/metrics.py` | net5 / net20 / accel / 象限 / 泡泡半徑 |
| `pipeline/verify.py` | BFI82U 對帳與欄位恆等式檢查 |
| `pipeline/run.py` | 管線進入點，產出 `data/latest.json` |
| `web/index.html` | 頁面骨架 |
| `web/chart.js` | 泡泡圖 SVG 繪製 |
| `web/app.js` | 資料載入、排行榜、板塊詳情 |
| `web/style.css` | 樣式與深淺色主題 |
| `tests/fixtures/` | 真實端點回應樣本（提交進版控） |
| `reports/unmapped_*.txt` | 每次執行產出的死代號報表 |

> 本表取代規格第 8 節的檔案結構草案。規格當時把抓取與清洗合稱 `fetch.py`／`clean.py`／`compute.py`，
> 實際切分改以責任為界：`sources`（抓取快取）、`parsers`（正規化工具）、`extract`（端點解析）、
> `aggregate`（彙總）、`metrics`（指標）。以本表為準。

## 端點欄位索引（已實測確認）

實作時直接引用這些索引，不要重新推導。

```
T86（上市法人，單位：股數）
  [0] 證券代號  [1] 證券名稱
  [4] 外陸資買賣超(不含外資自營商)   [7] 外資自營商買賣超
  [10] 投信買賣超  [11] 自營商買賣超  [18] 三大法人買賣超

MI_INDEX（上市收盤行情，tables 中 fields 含「收盤價」的那一張）
  [0] 證券代號  [1] 證券名稱  [8] 收盤價
  [9] 漲跌(+/-) 含 HTML  [10] 漲跌價差

TPEX insti（上櫃法人，單位：股數，tables[0]）
  [0] 代號  [1] 名稱
  [10] 外資合計買賣超  [13] 投信買賣超
  [22] 自營商合計買賣超  [23] 三大法人買賣超合計

TPEX otc（上櫃收盤行情，tables[0]）
  [0] 代號  [1] 名稱  [2] 收盤  [3] 漲跌

BFI82U（對帳基準，單位：元）
  data 中 [0] 以「合計」開頭的那一列：
  [1] 買進金額  [2] 賣出金額  [3] 買賣差額
```

---

### Task 1: 專案骨架與真實回應樣本

建立套件結構，並把五支端點的真實回應存成測試樣本。後續所有解析測試都打這些樣本，不連網。

**Files:**
- Create: `pipeline/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_fixtures.py`, `scripts/fetch_fixtures.py`, `.gitignore`
- Create: `tests/fixtures/*.json`（由腳本產生）

**Interfaces:**
- Consumes: 無
- Produces: `tests/conftest.py` 提供 session 範圍 fixture `t86_raw`、`mi_index_raw`、`tpex_insti_raw`、`tpex_otc_raw`、`bfi_raw`，各回傳該端點 2026-09-16 的完整 JSON dict。

- [ ] **Step 1: 建立目錄與 `.gitignore`**

```bash
mkdir -p pipeline tests/fixtures scripts data/raw data/daily
touch pipeline/__init__.py tests/__init__.py
```

`.gitignore` 內容：
```
__pycache__/
*.pyc
.pytest_cache/
data/raw/
data/daily/
data/latest.json
```

- [ ] **Step 2: 寫下載樣本的腳本**

`scripts/fetch_fixtures.py`:
```python
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
```

- [ ] **Step 3: 執行腳本產生樣本**

Run: `python scripts/fetch_fixtures.py`
Expected: 印出五個檔案大小。`t86` 約 3–4 MB、`mi_index` 約 4–5 MB、`tpex_otc` 約 400 KB、`tpex_insti` 約 300 KB、`bfi` 約 1 KB。

- [ ] **Step 4: 寫 conftest 提供樣本 fixture**

`tests/conftest.py`:
```python
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}_20260916.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def t86_raw() -> dict:
    return _load("t86")


@pytest.fixture(scope="session")
def mi_index_raw() -> dict:
    return _load("mi_index")


@pytest.fixture(scope="session")
def tpex_insti_raw() -> dict:
    return _load("tpex_insti")


@pytest.fixture(scope="session")
def tpex_otc_raw() -> dict:
    return _load("tpex_otc")


@pytest.fixture(scope="session")
def bfi_raw() -> dict:
    return _load("bfi")
```

- [ ] **Step 5: 寫樣本完整性測試**

`tests/test_fixtures.py`:
```python
def test_t86_shape(t86_raw):
    assert t86_raw["stat"] == "OK"
    assert t86_raw["date"] == "20260916"
    assert len(t86_raw["fields"]) == 19
    assert len(t86_raw["data"]) == 16893


def test_mi_index_has_close_table(mi_index_raw):
    tables = [t for t in mi_index_raw["tables"] if "收盤價" in t.get("fields", [])]
    assert len(tables) == 1
    assert len(tables[0]["fields"]) == 16


def test_tpex_insti_shape(tpex_insti_raw):
    table = tpex_insti_raw["tables"][0]
    assert table["date"] == "115/09/16"
    assert len(table["fields"]) == 24
    assert len(table["data"]) == 886


def test_tpex_otc_shape(tpex_otc_raw):
    table = tpex_otc_raw["tables"][0]
    assert table["date"] == "115/09/16"
    assert len(table["data"]) == 1014


def test_bfi_has_total_row(bfi_raw):
    totals = [r for r in bfi_raw["data"] if r[0].startswith("合計")]
    assert len(totals) == 1
    assert totals[0][3] == "-20,308,782,437"
```

- [ ] **Step 6: 執行測試**

Run: `python -m pytest tests/test_fixtures.py -v`
Expected: 5 passed

- [ ] **Step 7: 提交**

```bash
git add pipeline tests scripts .gitignore
git commit -m "chore: 建立專案骨架與交易所回應樣本"
```

---

### Task 2: 數值解析與日期轉換工具

四支端點的數字都帶千分位逗號，部分欄位含 HTML 或以 `--` 表示空值，TPEX 用民國年。這些共用工具先做。

**Files:**
- Create: `pipeline/parsers.py`
- Test: `tests/test_parsers.py`

**Interfaces:**
- Consumes: 無
- Produces:
  - `to_number(value) -> float` — 千分位、正負號、空值、HTML 一律吃下，無法解析回 `0.0`
  - `strip_html(value: str) -> str`
  - `roc_to_iso(value: str) -> str` — `"115/09/16"` → `"2026-09-16"`
  - `iso_to_twse(value: str) -> str` — `"2026-09-16"` → `"20260916"`
  - `iso_to_tpex(value: str) -> str` — `"2026-09-16"` → `"2026/09/16"`

- [ ] **Step 1: 寫失敗的測試**

`tests/test_parsers.py`:
```python
import pytest

from pipeline.parsers import iso_to_tpex, iso_to_twse, roc_to_iso, strip_html, to_number


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("101,420,290", 101420290.0),
        ("-1,069,000", -1069000.0),
        ("2,380.00", 2380.0),
        ("0", 0.0),
        ("", 0.0),
        ("--", 0.0),
        ("---", 0.0),
        ("X", 0.0),
        (None, 0.0),
        (1234, 1234.0),
        ("+7.50", 7.5),
        ("<p style= color:red>+</p>", 0.0),
    ],
)
def test_to_number(raw, expected):
    assert to_number(raw) == expected


def test_strip_html():
    assert strip_html("<p style= color:red>+</p>") == "+"
    assert strip_html("<p>X</p>") == "X"
    assert strip_html("最後買量<br>(張數)") == "最後買量(張數)"
    assert strip_html("  中美晶  ") == "中美晶"


def test_roc_to_iso():
    assert roc_to_iso("115/09/16") == "2026-09-16"
    assert roc_to_iso("99/01/02") == "2010-01-02"


def test_iso_converters():
    assert iso_to_twse("2026-09-16") == "20260916"
    assert iso_to_tpex("2026-09-16") == "2026/09/16"
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_parsers.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'pipeline.parsers'`

- [ ] **Step 3: 實作**

`pipeline/parsers.py`:
```python
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
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_parsers.py -v`
Expected: 15 passed

- [ ] **Step 5: 提交**

```bash
git add pipeline/parsers.py tests/test_parsers.py
git commit -m "feat: 新增數值解析與民國年轉換工具"
```

---

### Task 3: 上市資料擷取（T86 與 MI_INDEX）

把 TWSE 兩支端點的回應轉成正規化資料列。本任務包含**欄位恆等式測試**，這是欄位索引是否正確的決定性驗證。

**Files:**
- Create: `pipeline/extract.py`
- Test: `tests/test_extract_twse.py`

**Interfaces:**
- Consumes: `pipeline.parsers.to_number`、`strip_html`
- Produces:
  - `extract_t86(raw: dict) -> list[dict]` — 每列 `{"code": str, "name": str, "net_shares": float, "market": "TWSE"}`，**不過濾**，回傳全部 16893 列
  - `extract_mi_index(raw: dict) -> dict[str, dict]` — `{code: {"name": str, "close": float, "chg": float}}`，**不過濾**
  - `is_stock(code: str) -> bool` — 恰好 4 位數字才為 True

- [ ] **Step 1: 寫失敗的測試**

`tests/test_extract_twse.py`:
```python
from pipeline.extract import extract_mi_index, extract_t86, is_stock
from pipeline.parsers import to_number


def test_is_stock():
    assert is_stock("2330") is True
    assert is_stock("0050") is True
    assert is_stock("031234") is False   # 權證，6 位
    assert is_stock("00411A") is False   # 含英文
    assert is_stock("12345") is False    # 5 位


def test_extract_t86_returns_all_rows(t86_raw):
    rows = extract_t86(t86_raw)
    assert len(rows) == 16893
    assert all(isinstance(r["code"], str) for r in rows)
    assert all(r["market"] == "TWSE" for r in rows)


def test_extract_t86_known_row(t86_raw):
    rows = {r["code"]: r for r in extract_t86(t86_raw)}
    au = rows["2409"]
    assert au["name"] == "友達"
    assert au["net_shares"] == 56611082.0


def test_extract_t86_stock_count(t86_raw):
    rows = extract_t86(t86_raw)
    assert sum(1 for r in rows if is_stock(r["code"])) == 1075


def test_t86_column_identity(t86_raw):
    """三大法人 == 外陸資 + 外資自營商 + 投信 + 自營商。

    此恆等式在 16893 列上零違反；違反即表示欄位索引錯位。
    """
    for row in t86_raw["data"]:
        parts = to_number(row[4]) + to_number(row[7]) + to_number(row[10]) + to_number(row[11])
        assert abs(parts - to_number(row[18])) < 0.5, row[0]


def test_t86_dealer_identity(t86_raw):
    """自營商買賣超 == 自行買賣 + 避險。"""
    for row in t86_raw["data"]:
        parts = to_number(row[14]) + to_number(row[17])
        assert abs(parts - to_number(row[11])) < 0.5, row[0]


def test_extract_mi_index(mi_index_raw):
    prices = extract_mi_index(mi_index_raw)
    assert prices["2330"]["name"] == "台積電"
    assert prices["2330"]["close"] == 2380.0
    assert prices["2330"]["chg"] == 0.0
    assert sum(1 for c in prices if is_stock(c)) == 1092


def test_extract_mi_index_strips_html(mi_index_raw):
    """漲跌欄含 <p> 標籤，不得污染數值。"""
    prices = extract_mi_index(mi_index_raw)
    assert all(isinstance(v["chg"], float) for v in prices.values())
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_extract_twse.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'pipeline.extract'`

- [ ] **Step 3: 實作**

`pipeline/extract.py`:
```python
"""四支端點回應 → 正規化資料列。欄位索引見計畫文件，已實測確認。"""
import re

from pipeline.parsers import strip_html, to_number

_STOCK = re.compile(r"^\d{4}$")

# T86 欄位索引
T86_CODE, T86_NAME, T86_NET = 0, 1, 18
# MI_INDEX 欄位索引
MI_CODE, MI_NAME, MI_CLOSE, MI_CHG = 0, 1, 8, 10


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
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_extract_twse.py -v`
Expected: 8 passed（恆等式測試會跑 16893 列，約需數秒）

- [ ] **Step 5: 提交**

```bash
git add pipeline/extract.py tests/test_extract_twse.py
git commit -m "feat: 新增上市 T86 與 MI_INDEX 資料擷取"
```

---

### Task 4: 上櫃資料擷取（TPEX insti 與 otc）

TPEX 的欄位名有七組重複的「買進股數／賣出股數／買賣超股數」，只能靠索引定位。本任務同樣以恆等式測試鎖定索引正確性。

**Files:**
- Modify: `pipeline/extract.py`
- Test: `tests/test_extract_tpex.py`

**Interfaces:**
- Consumes: `pipeline.parsers.to_number`、`strip_html`
- Produces:
  - `extract_tpex_insti(raw: dict) -> list[dict]` — 格式同 `extract_t86`，但 `"market": "TPEX"`
  - `extract_tpex_otc(raw: dict) -> dict[str, dict]` — 格式同 `extract_mi_index`

- [ ] **Step 1: 寫失敗的測試**

`tests/test_extract_tpex.py`:
```python
from pipeline.extract import extract_tpex_insti, extract_tpex_otc, is_stock
from pipeline.parsers import to_number


def test_extract_tpex_insti_rows(tpex_insti_raw):
    rows = extract_tpex_insti(tpex_insti_raw)
    assert len(rows) == 886
    assert all(r["market"] == "TPEX" for r in rows)


def test_extract_tpex_insti_known_row(tpex_insti_raw):
    rows = {r["code"]: r for r in extract_tpex_insti(tpex_insti_raw)}
    sas = rows["5483"]
    assert sas["name"] == "中美晶"
    assert sas["net_shares"] == 4250116.0


def test_tpex_total_identity(tpex_insti_raw):
    """三大法人合計 == 外資合計 + 投信 + 自營商合計。

    此恆等式在 886 列上零違反；違反即表示欄位索引錯位。
    """
    for row in tpex_insti_raw["tables"][0]["data"]:
        parts = to_number(row[10]) + to_number(row[13]) + to_number(row[22])
        assert abs(parts - to_number(row[23])) < 0.5, row[0]


def test_tpex_foreign_identity(tpex_insti_raw):
    """外資合計 == 外陸資(不含外資自營商) + 外資自營商。"""
    for row in tpex_insti_raw["tables"][0]["data"]:
        parts = to_number(row[4]) + to_number(row[7])
        assert abs(parts - to_number(row[10])) < 0.5, row[0]


def test_tpex_dealer_identity(tpex_insti_raw):
    """自營商合計 == 自行買賣 + 避險。"""
    for row in tpex_insti_raw["tables"][0]["data"]:
        parts = to_number(row[16]) + to_number(row[19])
        assert abs(parts - to_number(row[22])) < 0.5, row[0]


def test_extract_tpex_otc(tpex_otc_raw):
    prices = extract_tpex_otc(tpex_otc_raw)
    assert len(prices) == 1014
    assert prices["5483"]["name"] == "中美晶"
    assert prices["5483"]["close"] == 183.5
    assert prices["5483"]["chg"] == 7.5


def test_tpex_otc_stock_codes_are_strings(tpex_otc_raw):
    prices = extract_tpex_otc(tpex_otc_raw)
    assert all(isinstance(c, str) for c in prices)
    assert any(is_stock(c) for c in prices)
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_extract_tpex.py -v`
Expected: FAIL，`ImportError: cannot import name 'extract_tpex_insti'`

- [ ] **Step 3: 實作（追加至 `pipeline/extract.py` 末尾）**

```python
# TPEX insti 欄位索引（欄位名七組重複，只能靠索引）
TPEX_CODE, TPEX_NAME, TPEX_NET = 0, 1, 23
# TPEX otc 欄位索引
OTC_CODE, OTC_NAME, OTC_CLOSE, OTC_CHG = 0, 1, 2, 3


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
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_extract_tpex.py -v`
Expected: 7 passed

- [ ] **Step 5: 全部測試回歸**

Run: `python -m pytest -v`
Expected: 35 passed

- [ ] **Step 6: 提交**

```bash
git add pipeline/extract.py tests/test_extract_tpex.py
git commit -m "feat: 新增上櫃法人與收盤行情資料擷取"
```

---

### Task 5: 板塊定義載入

讀取 `sectors.yaml` 並驗證結構。代號必須是字串，不得有空板塊。

**Files:**
- Create: `pipeline/sectors.py`
- Test: `tests/test_sectors.py`

**Interfaces:**
- Consumes: `sectors.yaml`（專案根目錄，76 板塊 601 檔）
- Produces:
  - `load_sectors(path: str | Path | None = None) -> dict[str, list[str]]`
  - `all_codes(sectors: dict) -> set[str]`

- [ ] **Step 1: 寫失敗的測試**

`tests/test_sectors.py`:
```python
import pytest

from pipeline.sectors import all_codes, load_sectors


@pytest.fixture(scope="session")
def sectors():
    return load_sectors()


def test_sector_count(sectors):
    assert len(sectors) == 76


def test_unique_code_count(sectors):
    assert len(all_codes(sectors)) == 601


def test_codes_are_strings(sectors):
    for name, codes in sectors.items():
        for code in codes:
            assert isinstance(code, str), f"{name} 的 {code!r} 不是字串"


def test_no_empty_sector(sectors):
    for name, codes in sectors.items():
        assert len(codes) > 0, f"{name} 沒有成分股"


def test_no_duplicate_within_sector(sectors):
    for name, codes in sectors.items():
        assert len(codes) == len(set(codes)), f"{name} 有重複代號"


def test_known_sector_membership(sectors):
    assert "2317" in sectors["AI 伺服器組裝"]
    assert "3706" in sectors["AI 伺服器組裝"]   # 神達，已由 2315 替換
    assert "2315" not in all_codes(sectors)     # 舊代號應已清除
    assert "3576" in sectors["太陽能產業"]       # 聯合再生
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_sectors.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'pipeline.sectors'`

- [ ] **Step 3: 實作**

`pipeline/sectors.py`:
```python
"""板塊定義載入。sectors.yaml 由死代號清理產出，見 reports/dead-codes-2026-09-18.md。"""
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "sectors.yaml"


def load_sectors(path=None) -> dict[str, list[str]]:
    """載入板塊定義並驗證結構。代號保持字串，避免掉前導零。"""
    target = Path(path) if path else DEFAULT_PATH
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("sectors.yaml 頂層必須是板塊名稱對應成分股清單")
    for name, codes in data.items():
        if not codes:
            raise ValueError(f"板塊「{name}」沒有成分股")
        for code in codes:
            if not isinstance(code, str):
                raise ValueError(f"板塊「{name}」的代號 {code!r} 不是字串，請在 YAML 中加引號")
    return data


def all_codes(sectors: dict[str, list[str]]) -> set[str]:
    """所有板塊的成分股去重集合。個股可同時屬於多個板塊。"""
    return {code for codes in sectors.values() for code in codes}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_sectors.py -v`
Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add pipeline/sectors.py tests/test_sectors.py
git commit -m "feat: 新增板塊定義載入與結構驗證"
```

---

### Task 6: 金額換算與板塊彙總

把股數換算成億元，再依板塊加總。個股可屬多個板塊，各板塊獨立計算。

**Files:**
- Create: `pipeline/aggregate.py`
- Test: `tests/test_aggregate.py`

**Interfaces:**
- Consumes: `extract_t86`、`extract_tpex_insti`、`extract_mi_index`、`extract_tpex_otc`、`load_sectors`
- Produces:
  - `to_stock_flows(insti_rows: list[dict], prices: dict[str, dict]) -> dict[str, dict]` — `{code: {"name","market","net_yi","close","chg"}}`，只保留 `is_stock` 且有價格者
  - `aggregate_sectors(sectors: dict, flows: dict) -> dict[str, dict]` — `{sector: {"net_yi": float, "size": int, "stocks": list[str]}}`
  - `YI = 1e8`

- [ ] **Step 1: 寫失敗的測試**

`tests/test_aggregate.py`:
```python
from pipeline.aggregate import YI, aggregate_sectors, to_stock_flows


def test_yi_constant():
    assert YI == 1e8


def test_to_stock_flows_converts_to_yi():
    insti = [{"code": "2330", "name": "台積電", "net_shares": 1_000_000.0, "market": "TWSE"}]
    prices = {"2330": {"name": "台積電", "close": 1000.0, "chg": 5.0}}
    flows = to_stock_flows(insti, prices)
    # 100 萬股 × 1000 元 = 10 億元
    assert flows["2330"]["net_yi"] == 10.0
    assert flows["2330"]["close"] == 1000.0
    assert flows["2330"]["chg"] == 5.0
    assert flows["2330"]["market"] == "TWSE"


def test_to_stock_flows_filters_non_stock():
    insti = [
        {"code": "2330", "name": "台積電", "net_shares": 1000.0, "market": "TWSE"},
        {"code": "031234", "name": "某權證", "net_shares": 9e9, "market": "TWSE"},
    ]
    prices = {"2330": {"name": "台積電", "close": 100.0, "chg": 0.0},
              "031234": {"name": "某權證", "close": 1.0, "chg": 0.0}}
    flows = to_stock_flows(insti, prices)
    assert set(flows) == {"2330"}


def test_to_stock_flows_skips_missing_price():
    insti = [{"code": "9999", "name": "無價股", "net_shares": 1000.0, "market": "TWSE"}]
    flows = to_stock_flows(insti, {})
    assert flows == {}


def test_aggregate_sectors_sums_members():
    sectors = {"測試板塊": ["1111", "2222"], "另一板塊": ["2222"]}
    flows = {
        "1111": {"name": "A", "market": "TWSE", "net_yi": 3.0, "close": 10.0, "chg": 0.0},
        "2222": {"name": "B", "market": "TPEX", "net_yi": -1.0, "close": 20.0, "chg": 0.0},
    }
    result = aggregate_sectors(sectors, flows)
    assert result["測試板塊"]["net_yi"] == 2.0
    assert result["測試板塊"]["size"] == 2
    assert result["另一板塊"]["net_yi"] == -1.0
    assert result["另一板塊"]["size"] == 1


def test_aggregate_sectors_ignores_absent_members():
    """成分股當日無資料時不計入 size，板塊仍存在。"""
    sectors = {"測試板塊": ["1111", "8888"]}
    flows = {"1111": {"name": "A", "market": "TWSE", "net_yi": 5.0, "close": 1.0, "chg": 0.0}}
    result = aggregate_sectors(sectors, flows)
    assert result["測試板塊"]["net_yi"] == 5.0
    assert result["測試板塊"]["size"] == 1
    assert result["測試板塊"]["stocks"] == ["1111"]


def test_real_data_end_to_end(t86_raw, mi_index_raw, tpex_insti_raw, tpex_otc_raw):
    """以真實樣本跑一遍，確認 76 板塊都算得出數字。"""
    from pipeline.extract import (
        extract_mi_index,
        extract_t86,
        extract_tpex_insti,
        extract_tpex_otc,
    )
    from pipeline.sectors import load_sectors

    insti = extract_t86(t86_raw) + extract_tpex_insti(tpex_insti_raw)
    prices = {**extract_mi_index(mi_index_raw), **extract_tpex_otc(tpex_otc_raw)}
    flows = to_stock_flows(insti, prices)
    sectors = load_sectors()
    result = aggregate_sectors(sectors, flows)
    assert len(result) == 76
    assert all(r["size"] > 0 for r in result.values()), "有板塊一檔都對不上"
    # 601 檔成分股應幾乎全數對上（允許當日停牌等少數缺漏）
    covered = len({c for r in result.values() for c in r["stocks"]})
    assert covered >= 590, f"只對上 {covered} 檔"
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_aggregate.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'pipeline.aggregate'`

- [ ] **Step 3: 實作**

`pipeline/aggregate.py`:
```python
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
        out[code] = {
            "name": row["name"] or price["name"],
            "market": row["market"],
            "net_yi": row["net_shares"] * price["close"] / YI,
            "close": price["close"],
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
            "size": len(present),
            "stocks": present,
        }
    return result
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_aggregate.py -v`
Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add pipeline/aggregate.py tests/test_aggregate.py
git commit -m "feat: 新增金額換算與板塊彙總"
```

---

### Task 7: 指標計算

由每日板塊淨買超序列算出 net5 / net20 / accel / 象限 / 泡泡半徑。定義取自原站公開前端程式碼，見規格第 5 節。

**Files:**
- Create: `pipeline/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Consumes: 無（純計算）
- Produces:
  - `window_sum(values: list[float], n: int) -> float` — 取序列**末端** n 個值加總，不足 n 個則全取
  - `accel(net5: float, net20: float) -> float` — `net5 / 5 - net20 / 20`
  - `quadrant(net5: float, acc: float) -> str` — 回傳 `"surge"` / `"rotation"` / `"watch"` / `"ebb"`
  - `radius(net20: float, max20: float) -> float` — 夾在 22–55
  - `build_metrics(history: list[dict[str, float]]) -> list[dict]` — `history` 依日期**由舊到新**排序，每元素為 `{板塊名: net_yi}`；回傳每板塊的完整指標

- [ ] **Step 1: 寫失敗的測試**

`tests/test_metrics.py`:
```python
import pytest

from pipeline.metrics import accel, build_metrics, quadrant, radius, window_sum


def test_window_sum_takes_tail():
    assert window_sum([1, 2, 3, 4, 5], 3) == 12.0      # 3+4+5
    assert window_sum([1, 2], 5) == 3.0                # 不足則全取
    assert window_sum([], 5) == 0.0


def test_accel():
    # net5=10 → 日均 2.0；net20=20 → 日均 1.0；加速度 +1.0
    assert accel(10.0, 20.0) == 1.0
    assert accel(5.0, 20.0) == 0.0
    assert accel(0.0, 20.0) == -1.0


@pytest.mark.parametrize(
    "net5,acc,expected",
    [
        (1.0, 1.0, "surge"),      # 右上：錢在流進而且越流越快
        (1.0, -1.0, "rotation"),  # 右下：還在流進但慢下來了
        (1.0, 0.0, "rotation"),   # accel == 0 歸於輪動
        (-1.0, 1.0, "watch"),     # 左上：流出但在減緩
        (-1.0, -1.0, "ebb"),      # 左下：退潮
        (0.0, 1.0, "watch"),      # net5 == 0 歸於觀察側
        (0.0, -1.0, "ebb"),
    ],
)
def test_quadrant(net5, acc, expected):
    assert quadrant(net5, acc) == expected


def test_radius_bounds():
    assert radius(0.0, 100.0) == 22.0
    assert radius(100.0, 100.0) == 55.0
    assert radius(-100.0, 100.0) == 55.0        # 取絕對值
    assert 22.0 < radius(50.0, 100.0) < 55.0


def test_radius_handles_zero_max():
    assert radius(0.0, 0.0) == 22.0


def test_build_metrics_basic():
    history = [{"A": 1.0, "B": -1.0} for _ in range(20)]
    out = {m["name"]: m for m in build_metrics(history)}
    assert out["A"]["net_5d_yi"] == 5.0
    assert out["A"]["net_20d_yi"] == 20.0
    assert out["A"]["net_1d_yi"] == 1.0
    assert out["A"]["accel"] == 0.0
    assert out["A"]["quadrant"] == "rotation"
    assert out["B"]["quadrant"] == "ebb"


def test_build_metrics_radius_relative_to_max():
    history = [{"大": 10.0, "小": 1.0} for _ in range(20)]
    out = {m["name"]: m for m in build_metrics(history)}
    assert out["大"]["radius"] == 55.0
    assert out["小"]["radius"] < 55.0


def test_build_metrics_requires_history():
    with pytest.raises(ValueError):
        build_metrics([])
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_metrics.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'pipeline.metrics'`

- [ ] **Step 3: 實作**

`pipeline/metrics.py`:
```python
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
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_metrics.py -v`
Expected: 14 passed

- [ ] **Step 5: 提交**

```bash
git add pipeline/metrics.py tests/test_metrics.py
git commit -m "feat: 新增泡泡圖指標計算"
```

---

### Task 8: BFI82U 對帳驗證

量級健檢，可捕捉欄位錯位與單位錯誤。**必須用 T86 全體證券，不可用過濾後的股票集合**——BFI82U 涵蓋整個集中市場，權證是自營商避險大宗，只算 4 位數代號會有 77% 誤差。分母必須是成交總額，不可用淨額（淨額趨近零時相對誤差會爆增）。

**Files:**
- Create: `pipeline/verify.py`
- Test: `tests/test_verify.py`

**Interfaces:**
- Consumes: `extract_t86`、`extract_mi_index`
- Produces:
  - `TOLERANCE = 0.005`
  - `reconcile(t86_raw: dict, mi_raw: dict, bfi_raw: dict) -> dict` — 回傳 `{"computed","reference","turnover","error_ratio","passed"}`

- [ ] **Step 1: 寫失敗的測試**

`tests/test_verify.py`:
```python
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
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_verify.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'pipeline.verify'`

- [ ] **Step 3: 實作**

`pipeline/verify.py`:
```python
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
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_verify.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add pipeline/verify.py tests/test_verify.py
git commit -m "feat: 新增 BFI82U 對帳驗證"
```

---

### Task 9: 抓取、快取與管線進入點

串起整條管線並產出 `data/latest.json`。原始回應寫入 `data/raw/` 快取，重跑不重打交易所。

**Files:**
- Create: `pipeline/sources.py`, `pipeline/run.py`
- Test: `tests/test_sources.py`

**Interfaces:**
- Consumes: 前述所有模組
- Produces:
  - `sources.fetch(kind: str, date_iso: str, use_cache: bool = True) -> dict | None` — `kind` 為 `"t86"|"mi_index"|"bfi"|"tpex_insti"|"tpex_otc"`；非交易日回 `None`
  - `sources.is_empty(kind: str, payload: dict) -> bool`
  - `run.build(end_date: str, days: int = 20) -> dict` — 產出並寫檔，回傳 `latest.json` 的內容
  - `run.write_unmapped_report(sectors: dict, flows: dict, date_iso: str) -> None` — 輸出 `reports/unmapped_{YYYYMMDD}.txt`

**`data/latest.json` 結構：**
```json
{
  "date": "2026-09-16",
  "generated_at": "2026-09-18T10:00:00",
  "trading_days": 20,
  "reconciliation": {"error_ratio": 0.00023, "passed": true},
  "sectors": [
    {
      "name": "AI 伺服器組裝",
      "size": 12,
      "net_1d_yi": 1.23,
      "net_5d_yi": 5.67,
      "net_20d_yi": 20.1,
      "accel": 0.129,
      "quadrant": "surge",
      "radius": 33.2,
      "stocks": [
        {"code": "2317", "name": "鴻海", "market": "TWSE",
         "net_1d_yi": 0.5, "close": 215.5, "chg": 1.2}
      ]
    }
  ]
}
```

- [ ] **Step 1: 寫失敗的測試**

`tests/test_sources.py`:
```python
from pipeline.sources import build_url, is_empty


def test_build_url_twse_uses_compact_date():
    url = build_url("t86", "2026-09-16")
    assert "date=20260916" in url
    assert "selectType=ALL" in url


def test_build_url_tpex_uses_slash_date():
    url = build_url("tpex_insti", "2026-09-16")
    assert "date=2026/09/16" in url


def test_build_url_rejects_unknown_kind():
    import pytest

    with pytest.raises(KeyError):
        build_url("nope", "2026-09-16")


def test_is_empty_detects_holiday_twse():
    assert is_empty("t86", {"stat": "OK", "data": []}) is True
    assert is_empty("t86", {"stat": "OK", "data": [["2330"]]}) is False


def test_is_empty_detects_holiday_tpex():
    assert is_empty("tpex_insti", {"tables": [{"data": []}]}) is True
    assert is_empty("tpex_insti", {"tables": []}) is True
    assert is_empty("tpex_insti", {"tables": [{"data": [["5483"]]}]}) is False


def test_is_empty_on_real_fixtures(t86_raw, tpex_insti_raw):
    assert is_empty("t86", t86_raw) is False
    assert is_empty("tpex_insti", tpex_insti_raw) is False
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_sources.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'pipeline.sources'`

- [ ] **Step 3: 實作 `pipeline/sources.py`**

```python
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
    """非交易日回空表。TWSE 為 data 空陣列，TPEX 為 tables 空或其 data 空。"""
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
        resp = requests.get(build_url(kind, date_iso), headers=HEADERS, timeout=40)
        resp.raise_for_status()
        payload = resp.json()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        time.sleep(REQUEST_GAP)
    return None if is_empty(kind, payload) else payload
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_sources.py -v`
Expected: 6 passed

- [ ] **Step 5: 實作 `pipeline/run.py`**

```python
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
from pipeline.metrics import build_metrics
from pipeline.sectors import load_sectors
from pipeline.sources import fetch
from pipeline.verify import reconcile

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KINDS = ("t86", "mi_index", "bfi", "tpex_insti", "tpex_otc")
MAX_LOOKBACK = 90  # 回補時最多往前找幾個日曆日


def load_day(date_iso: str) -> dict | None:
    """抓取單日的五支端點。任一支缺資料即視為非交易日。"""
    payloads = {}
    for kind in KINDS:
        payload = fetch(kind, date_iso)
        if payload is None:
            return None
        payloads[kind] = payload
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


def build(end_date: str, days: int = 20) -> dict:
    """回補 days 個交易日並產出 latest.json。"""
    sectors = load_sectors()
    cursor = dt.date.fromisoformat(end_date)
    collected: list[tuple[str, dict, dict]] = []

    for _ in range(MAX_LOOKBACK):
        if len(collected) >= days:
            break
        date_iso = cursor.isoformat()
        payloads = load_day(date_iso)
        if payloads is not None:
            agg, flows = day_sector_nets(payloads, sectors)
            collected.append((date_iso, agg, flows))
            print(f"  {date_iso} 交易日，{len(flows)} 檔有資料")
        cursor -= dt.timedelta(days=1)

    if len(collected) < days:
        raise RuntimeError(f"只取得 {len(collected)} 個交易日，不足 {days} 個")

    collected.reverse()  # 由舊到新
    history = [{name: agg[name]["net_yi"] for name in agg} for _, agg, _ in collected]
    metrics = build_metrics(history)

    latest_date, latest_agg, latest_flows = collected[-1]
    payloads = load_day(latest_date)
    recon = reconcile(payloads["t86"], payloads["mi_index"], payloads["bfi"])
    if not recon["passed"]:
        raise RuntimeError(
            f"對帳未通過：誤差率 {recon['error_ratio']:.4%}，超過容差。不產出資料。"
        )

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
                        "net_1d_yi": round(latest_flows[code]["net_yi"], 4),
                        "close": latest_flows[code]["close"],
                        "chg": latest_flows[code]["chg"],
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
    args = parser.parse_args()

    print(f"回補至 {args.date}，目標 {args.days} 個交易日")
    result = build(args.date, args.days)
    print(f"完成：{result['date']}，{len(result['sectors'])} 個板塊")
    print(f"對帳誤差率 {result['reconciliation']['error_ratio']:.4%}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 實跑管線**

Run: `python -m pipeline.run --date 2026-09-16 --days 20`
Expected: 逐日印出交易日與有資料檔數，接著印出死代號報表檔名，最後印出 76 個板塊與對帳誤差率（應 < 0.5%）。首次執行會抓約 100 次請求，需數分鐘；之後有快取會很快。

- [ ] **Step 7: 檢查輸出**

Run: `python -c "import json;d=json.load(open('data/latest.json',encoding='utf-8'));print(d['date'],len(d['sectors']));print([s['name'] for s in d['sectors'][:5]])"`
Expected: 印出日期、`76`、以及 net_5d_yi 最高的五個板塊名稱。

- [ ] **Step 8: 提交**

```bash
git add pipeline/sources.py pipeline/run.py tests/test_sources.py
git commit -m "feat: 新增端點抓取快取與管線進入點"
```

---

### Task 10: 泡泡圖繪製

> **實作前請先載入 `dataviz` skill** —— 這是資料視覺化，色彩與座標軸處理須依該 skill 的規範。本任務給定的色票為佔位值，請依 skill 指引確認對比度與深淺色表現。

四象限 SVG 泡泡圖。**不可使用 ES module**：頁面會以 `file://` 或簡易 HTTP server 開啟，module 在前者會被擋。一律用傳統 script 與全域物件。

**Files:**
- Create: `web/chart.js`
- Test: 以 Task 12 的瀏覽器驗收涵蓋（純繪圖邏輯，不寫單元測試）

**Interfaces:**
- Consumes: `data/latest.json` 的 `sectors` 陣列
- Produces: 全域 `window.TideChart`，含
  - `render(sectors: Array, container: HTMLElement, onSelect: (sector) => void): void`
  - `QUADRANT_LABEL: {surge:"漲潮", rotation:"輪動", watch:"觀察", ebb:"退潮"}`

- [ ] **Step 1: 建立 `web/chart.js`**

```javascript
(function (global) {
  'use strict';

  var QUADRANT_CLASS = {
    surge: 'q-surge',
    rotation: 'q-rotation',
    watch: 'q-watch',
    ebb: 'q-ebb'
  };

  var QUADRANT_LABEL = {
    surge: '漲潮',
    rotation: '輪動',
    watch: '觀察',
    ebb: '退潮'
  };

  var NS = 'http://www.w3.org/2000/svg';
  var PAD = 56;

  function el(tag, attrs, text) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if (Object.prototype.hasOwnProperty.call(attrs, k)) {
        node.setAttribute(k, attrs[k]);
      }
    }
    if (text != null) { node.textContent = text; }
    return node;
  }

  // domain 兩端各留 12% 餘裕，避免泡泡貼邊
  function extent(values) {
    var lo = Math.min.apply(null, values);
    var hi = Math.max.apply(null, values);
    if (lo === hi) { lo -= 1; hi += 1; }
    var span = hi - lo;
    return [lo - span * 0.12, hi + span * 0.12];
  }

  function scaler(domain, lo, hi) {
    var d0 = domain[0];
    var d1 = domain[1];
    return function (v) { return lo + (v - d0) / (d1 - d0) * (hi - lo); };
  }

  // 中文字約佔 1 em，英數約 0.55 em；超出泡泡寬度就截斷
  function clip(name, radius, fontSize) {
    var maxEm = (radius * 1.8) / fontSize;
    var width = 0;
    var out = '';
    for (var i = 0; i < name.length; i++) {
      var ch = name.charAt(i);
      var w = ch === ' ' ? 0.28 : ch.charCodeAt(0) < 0x2E80 ? 0.55 : 1;
      if (width + w > maxEm) { return out ? out + '…' : name.charAt(0) + '…'; }
      width += w;
      out += ch;
    }
    return out;
  }

  function render(sectors, container, onSelect) {
    container.innerHTML = '';
    if (!sectors || !sectors.length) { return; }

    var W = container.clientWidth || 900;
    var H = Math.max(420, Math.min(680, Math.round(W * 0.72)));

    var gx = scaler(extent(sectors.map(function (s) { return s.net_5d_yi; })), PAD, W - PAD);
    var gy = scaler(extent(sectors.map(function (s) { return s.accel; })), H - PAD, PAD);

    var svg = el('svg', {
      viewBox: '0 0 ' + W + ' ' + H,
      'class': 'bubble-chart',
      role: 'img',
      'aria-label': '板塊資金流四象限泡泡圖'
    });

    var x0 = gx(0);
    var y0 = gy(0);
    svg.appendChild(el('line', { x1: PAD, y1: y0, x2: W - PAD, y2: y0, 'class': 'axis' }));
    svg.appendChild(el('line', { x1: x0, y1: PAD, x2: x0, y2: H - PAD, 'class': 'axis' }));
    svg.appendChild(el('text', {
      x: W - PAD, y: y0 - 10, 'class': 'axis-label', 'text-anchor': 'end'
    }, '近 5 日買超（億）→'));
    svg.appendChild(el('text', {
      x: x0 + 10, y: PAD - 8, 'class': 'axis-label'
    }, '↑ 買超加速'));

    [
      ['surge', W - PAD - 6, PAD + 16, 'end'],
      ['rotation', W - PAD - 6, H - PAD - 10, 'end'],
      ['watch', PAD + 6, PAD + 16, 'start'],
      ['ebb', PAD + 6, H - PAD - 10, 'start']
    ].forEach(function (c) {
      svg.appendChild(el('text', {
        x: c[1], y: c[2], 'text-anchor': c[3],
        'class': 'quad-label ' + QUADRANT_CLASS[c[0]]
      }, QUADRANT_LABEL[c[0]]));
    });

    sectors.forEach(function (s) {
      var cx = gx(s.net_5d_yi);
      var cy = gy(s.accel);
      var r = s.radius;
      var fs = Math.max(10, Math.min(15, r * 0.34));

      var g = el('g', {
        'class': 'bubble ' + QUADRANT_CLASS[s.quadrant],
        tabindex: '0',
        role: 'button',
        'aria-label': s.name + ' ' + QUADRANT_LABEL[s.quadrant]
      });
      g.appendChild(el('circle', { cx: cx, cy: cy, r: r }));
      g.appendChild(el('text', {
        x: cx, y: cy - 1, 'class': 'b-name', 'text-anchor': 'middle', 'font-size': fs
      }, clip(s.name, r, fs)));
      g.appendChild(el('text', {
        x: cx, y: cy + fs + 2, 'class': 'b-val', 'text-anchor': 'middle', 'font-size': fs * 0.9
      }, (s.net_5d_yi >= 0 ? '+' : '') + s.net_5d_yi.toFixed(1)));
      g.appendChild(el('title', {},
        s.name + '：近 5 日 ' + s.net_5d_yi.toFixed(2) + ' 億、加速度 '
        + s.accel.toFixed(2) + '、成分股 ' + s.size + ' 檔'));

      function pick() { if (onSelect) { onSelect(s); } }
      g.addEventListener('click', pick);
      g.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); }
      });
      svg.appendChild(g);
    });

    container.appendChild(svg);
  }

  global.TideChart = { render: render, QUADRANT_LABEL: QUADRANT_LABEL };
}(window));
```

- [ ] **Step 2: 語法檢查**

Run: `node --check web/chart.js`
Expected: 無輸出（通過）。若機器無 node，改以瀏覽器主控台確認無語法錯誤。

- [ ] **Step 3: 提交**

```bash
git add web/chart.js
git commit -m "feat: 新增四象限泡泡圖 SVG 繪製"
```

---

### Task 11: 頁面、排行榜與板塊詳情

**重要：`fetch` 在 `file://` 下會被瀏覽器擋。** 必須以簡易 HTTP server 開啟，這在 Step 5 有明確指令。不要假設雙擊 HTML 可用。

**Files:**
- Create: `web/index.html`, `web/app.js`, `web/style.css`

**Interfaces:**
- Consumes: `window.TideChart.render`、`../data/latest.json`
- Produces: 可操作的頁面

- [ ] **Step 1: 建立 `web/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-TW" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tide 自製版｜台股板塊資金流</title>
<link rel="stylesheet" href="style.css">
<script>
// 首屏前套用主題，避免閃爍
(function () {
  try {
    var mode = localStorage.getItem('theme_mode') || 'system';
    var dark = mode === 'dark' || (mode === 'system'
      && (!window.matchMedia || matchMedia('(prefers-color-scheme: dark)').matches));
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  } catch (e) {
    document.documentElement.dataset.theme = 'dark';
  }
}());
</script>
</head>
<body>
<header class="top">
  <h1>台股板塊資金流</h1>
  <div class="meta">
    <span id="data-date">載入中…</span>
    <button id="theme-toggle" type="button" aria-label="切換深淺色">◐</button>
  </div>
</header>

<main>
  <section class="card">
    <div class="card-head">
      <h2>四象限泡泡圖</h2>
      <p class="hint">越右＝近 5 日買越多；越上＝比近 20 日平均更偏買。泡泡大小為近 20 日淨買超。</p>
    </div>
    <div id="chart"></div>
  </section>

  <section class="card">
    <div class="card-head">
      <h2>板塊排行</h2>
      <div class="tabs" role="tablist">
        <button class="tab active" data-sort="net_5d_yi" role="tab">近 5 日</button>
        <button class="tab" data-sort="net_1d_yi" role="tab">當日</button>
        <button class="tab" data-sort="net_20d_yi" role="tab">近 20 日</button>
      </div>
    </div>
    <div id="ranking"></div>
  </section>

  <section class="card" id="detail-card" hidden>
    <div class="card-head">
      <h2 id="detail-title">板塊詳情</h2>
      <button id="detail-close" type="button">關閉</button>
    </div>
    <div id="detail"></div>
  </section>
</main>

<footer>
  <p>資料來源：臺灣證券交易所、證券櫃檯買賣中心公開資訊。本頁僅彙整呈現公開資訊，不構成任何投資建議。</p>
</footer>

<script src="chart.js"></script>
<script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 建立 `web/app.js`**

```javascript
(function () {
  'use strict';

  var state = { data: null, sort: 'net_5d_yi' };

  function $(id) { return document.getElementById(id); }

  function signed(v, digits) {
    var d = digits == null ? 2 : digits;
    return (v >= 0 ? '+' : '') + v.toFixed(d);
  }

  function showError(message) {
    $('chart').innerHTML = '<p class="error">讀取資料失敗：' + message
      + '<br>請確認已執行 <code>python -m pipeline.run</code>，'
      + '並以 <code>python -m http.server</code> 開啟本頁。</p>';
  }

  function renderRanking() {
    var key = state.sort;
    var rows = state.data.sectors.slice().sort(function (a, b) { return b[key] - a[key]; });
    var html = '<table class="rank"><thead><tr>'
      + '<th>#</th><th>板塊</th><th>檔數</th><th class="num">當日</th>'
      + '<th class="num">近 5 日</th><th class="num">近 20 日</th><th>狀態</th>'
      + '</tr></thead><tbody>';
    rows.forEach(function (s, i) {
      html += '<tr data-name="' + s.name + '">'
        + '<td class="idx">' + (i + 1) + '</td>'
        + '<td class="name">' + s.name + '</td>'
        + '<td class="num dim">' + s.size + '</td>'
        + '<td class="num ' + (s.net_1d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(s.net_1d_yi) + '</td>'
        + '<td class="num ' + (s.net_5d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(s.net_5d_yi) + '</td>'
        + '<td class="num ' + (s.net_20d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(s.net_20d_yi) + '</td>'
        + '<td><span class="pill q-' + s.quadrant + '">'
        + window.TideChart.QUADRANT_LABEL[s.quadrant] + '</span></td>'
        + '</tr>';
    });
    $('ranking').innerHTML = html + '</tbody></table>';

    Array.prototype.forEach.call($('ranking').querySelectorAll('tr[data-name]'), function (tr) {
      tr.addEventListener('click', function () {
        var name = tr.getAttribute('data-name');
        var found = state.data.sectors.filter(function (s) { return s.name === name; })[0];
        if (found) { renderDetail(found); }
      });
    });
  }

  function renderDetail(sector) {
    $('detail-title').textContent = sector.name + '（' + sector.size + ' 檔）';
    var html = '<table class="rank"><thead><tr>'
      + '<th>代號</th><th>名稱</th><th>市場</th>'
      + '<th class="num">收盤</th><th class="num">漲跌</th><th class="num">法人買超（億）</th>'
      + '</tr></thead><tbody>';
    sector.stocks.forEach(function (st) {
      html += '<tr>'
        + '<td class="mono">' + st.code + '</td>'
        + '<td class="name">' + st.name + '</td>'
        + '<td class="dim">' + (st.market === 'TWSE' ? '上市' : '上櫃') + '</td>'
        + '<td class="num">' + st.close.toFixed(2) + '</td>'
        + '<td class="num ' + (st.chg >= 0 ? 'pos' : 'neg') + '">' + signed(st.chg) + '</td>'
        + '<td class="num ' + (st.net_1d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(st.net_1d_yi) + '</td>'
        + '</tr>';
    });
    $('detail').innerHTML = html + '</tbody></table>';
    $('detail-card').hidden = false;
    $('detail-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function paint() {
    $('data-date').textContent = '資料日期 ' + state.data.date
      + '（' + state.data.trading_days + ' 個交易日）';
    window.TideChart.render(state.data.sectors, $('chart'), renderDetail);
    renderRanking();
  }

  function bindControls() {
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (tab) {
      tab.addEventListener('click', function () {
        Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (t) {
          t.classList.remove('active');
        });
        tab.classList.add('active');
        state.sort = tab.getAttribute('data-sort');
        renderRanking();
      });
    });

    $('detail-close').addEventListener('click', function () {
      $('detail-card').hidden = true;
    });

    $('theme-toggle').addEventListener('click', function () {
      var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('theme_mode', next); } catch (e) { /* 隱私模式可能拋錯 */ }
    });

    var timer = null;
    window.addEventListener('resize', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (state.data) { window.TideChart.render(state.data.sectors, $('chart'), renderDetail); }
      }, 180);
    });
  }

  fetch('../data/latest.json', { cache: 'no-cache' })
    .then(function (r) {
      if (!r.ok) { throw new Error('HTTP ' + r.status); }
      return r.json();
    })
    .then(function (data) {
      state.data = data;
      bindControls();
      paint();
    })
    .catch(function (err) { showError(err.message); });
}());
```

- [ ] **Step 3: 建立 `web/style.css`**

```css
:root {
  --bg: #F4F7F5;
  --card: #FFFFFF;
  --text: #16201C;
  --dim: #6B7A73;
  --line: #DCE4DF;
  --pos: #C0392B;
  --neg: #1E8449;
  --surge: #1E8449;
  --rotation: #B7950B;
  --watch: #7F8C8D;
  --ebb: #C0392B;
}

:root[data-theme="dark"] {
  --bg: #0F1413;
  --card: #18201E;
  --text: #E8EFEB;
  --dim: #8B9A93;
  --line: #2A3532;
  --pos: #FF6B5B;
  --neg: #4ECB71;
  --surge: #4ECB71;
  --rotation: #E8C547;
  --watch: #94A3A0;
  --ebb: #FF6B5B;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 0 16px 48px;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", sans-serif;
  line-height: 1.6;
}

.top {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; max-width: 1080px; margin: 0 auto; padding: 20px 0;
}
.top h1 { font-size: 1.25rem; margin: 0; }
.meta { display: flex; align-items: center; gap: 12px; color: var(--dim); font-size: .875rem; }

button {
  background: var(--card); color: var(--text); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px 12px; cursor: pointer; font: inherit;
}
button:hover { border-color: var(--dim); }

main { max-width: 1080px; margin: 0 auto; display: grid; gap: 20px; }

.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px; }
.card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.card-head h2 { font-size: 1rem; margin: 0 0 6px; }
.hint { color: var(--dim); font-size: .8125rem; margin: 0 0 12px; flex-basis: 100%; }

.tabs { display: flex; gap: 6px; }
.tab { font-size: .8125rem; padding: 4px 10px; }
.tab.active { background: var(--text); color: var(--card); border-color: var(--text); }

.bubble-chart { width: 100%; height: auto; display: block; }
.axis { stroke: var(--line); stroke-width: 1; }
.axis-label { fill: var(--dim); font-size: 12px; }
.quad-label { font-size: 13px; font-weight: 600; opacity: .55; }

.bubble { cursor: pointer; }
.bubble circle { fill-opacity: .22; stroke-width: 1.5; }
.bubble:hover circle, .bubble:focus circle { fill-opacity: .38; }
.bubble:focus { outline: none; }
.bubble:focus circle { stroke-width: 3; }
.bubble text { pointer-events: none; }
.b-name { font-weight: 600; fill: var(--text); }
.b-val { fill: var(--dim); }

.q-surge circle { fill: var(--surge); stroke: var(--surge); }
.q-rotation circle { fill: var(--rotation); stroke: var(--rotation); }
.q-watch circle { fill: var(--watch); stroke: var(--watch); }
.q-ebb circle { fill: var(--ebb); stroke: var(--ebb); }
.quad-label.q-surge { fill: var(--surge); }
.quad-label.q-rotation { fill: var(--rotation); }
.quad-label.q-watch { fill: var(--watch); }
.quad-label.q-ebb { fill: var(--ebb); }

table.rank { width: 100%; border-collapse: collapse; font-size: .875rem; }
table.rank th, table.rank td { padding: 7px 8px; border-bottom: 1px solid var(--line); text-align: left; }
table.rank th { color: var(--dim); font-weight: 500; font-size: .8125rem; }
table.rank tbody tr { cursor: pointer; }
table.rank tbody tr:hover { background: var(--bg); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.idx, .dim { color: var(--dim); }
.pos { color: var(--pos); }
.neg { color: var(--neg); }

.pill { font-size: .75rem; padding: 2px 8px; border-radius: 999px; border: 1px solid currentColor; }
.pill.q-surge { color: var(--surge); }
.pill.q-rotation { color: var(--rotation); }
.pill.q-watch { color: var(--watch); }
.pill.q-ebb { color: var(--ebb); }

.error { color: var(--pos); }
footer { max-width: 1080px; margin: 24px auto 0; color: var(--dim); font-size: .75rem; }

@media (max-width: 640px) {
  .top h1 { font-size: 1.05rem; }
  table.rank th, table.rank td { padding: 6px 5px; font-size: .8125rem; }
  .card { padding: 14px; }
}
```

- [ ] **Step 4: 語法檢查**

Run: `node --check web/app.js`
Expected: 無輸出（通過）。

- [ ] **Step 5: 啟動本機伺服器並開啟頁面**

```bash
# 在專案根目錄執行（不是 web/ 底下）
python -m http.server 8000
```

瀏覽器開啟 `http://localhost:8000/web/index.html`。

**不要用雙擊開啟 HTML。** `file://` 下 `fetch` 會被瀏覽器的同源政策擋下，頁面會顯示讀取失敗。

Expected: 泡泡圖顯示 76 個泡泡分佈於四象限，排行榜列出 76 列，點泡泡或列會展開板塊詳情。

- [ ] **Step 6: 提交**

```bash
git add web/
git commit -m "feat: 新增頁面、排行榜與板塊詳情"
```

---

### Task 12: 端到端驗收

逐項核對規格第 9 節的驗證標準。這是最後一關，不通過不算完成。

**Files:**
- Create: `tests/test_acceptance.py`

**Interfaces:**
- Consumes: 全部模組與 `data/latest.json`
- Produces: 無（驗收用）

- [ ] **Step 1: 寫驗收測試**

`tests/test_acceptance.py`:
```python
"""端到端驗收，對應規格第 9 節。需先執行過 python -m pipeline.run。"""
import json
from pathlib import Path

import pytest

from pipeline.sectors import all_codes, load_sectors

LATEST = Path(__file__).resolve().parent.parent / "data" / "latest.json"


@pytest.fixture(scope="module")
def latest():
    if not LATEST.exists():
        pytest.skip("尚未產出 data/latest.json，請先執行 python -m pipeline.run")
    return json.loads(LATEST.read_text(encoding="utf-8"))


def test_v1_reconciliation_passed(latest):
    """驗證項 1：總額對帳誤差率 < 0.5%。"""
    assert latest["reconciliation"]["passed"] is True
    assert latest["reconciliation"]["error_ratio"] < 0.005


def test_v3_no_dead_codes(latest):
    """驗證項 3：sectors.yaml 中的代號應幾乎全數對得上當日資料。"""
    defined = all_codes(load_sectors())
    seen = {s["code"] for sec in latest["sectors"] for s in sec["stocks"]}
    missing = defined - seen
    assert len(missing) <= 11, f"對不上的代號過多：{sorted(missing)}"


def test_v4_metric_consistency(latest):
    """驗證項 4：accel 必須等於 net5/5 - net20/20。"""
    for sec in latest["sectors"]:
        expected = sec["net_5d_yi"] / 5 - sec["net_20d_yi"] / 20
        assert abs(sec["accel"] - expected) < 1e-9, sec["name"]


def test_v5_all_quadrants_present(latest):
    """驗證項 5：四個象限的分類規則正確，且至少各有一個板塊。"""
    for sec in latest["sectors"]:
        net5, acc, q = sec["net_5d_yi"], sec["accel"], sec["quadrant"]
        if net5 > 0 and acc > 0:
            assert q == "surge", sec["name"]
        elif net5 > 0:
            assert q == "rotation", sec["name"]
        elif acc > 0:
            assert q == "watch", sec["name"]
        else:
            assert q == "ebb", sec["name"]
    assert len({s["quadrant"] for s in latest["sectors"]}) >= 3


def test_radius_within_bounds(latest):
    for sec in latest["sectors"]:
        assert 22.0 <= sec["radius"] <= 55.0, sec["name"]


def test_structure(latest):
    assert len(latest["sectors"]) == 76
    assert latest["trading_days"] == 20
    for sec in latest["sectors"]:
        assert sec["size"] > 0, sec["name"]
        assert len(sec["stocks"]) == sec["size"]
```

- [ ] **Step 2: 執行驗收測試**

Run: `python -m pytest tests/test_acceptance.py -v`
Expected: 6 passed

- [ ] **Step 3: 執行完整測試套件**

Run: `python -m pytest -v`
Expected: 全部通過，無 skip（除非未跑管線）。

- [ ] **Step 4: 驗證項 2 —— 個股金額人工抽驗**

```bash
python -c "
import json
d = json.load(open('data/latest.json', encoding='utf-8'))
seen = {}
for sec in d['sectors']:
    for s in sec['stocks']:
        seen[s['code']] = s
for code in ['2330', '2317', '5483']:
    s = seen.get(code)
    if s:
        print(f\"{s['code']} {s['name']} 收盤={s['close']} 法人買超={s['net_1d_yi']:.4f} 億\")
"
```

取其中一檔，到交易所網站對照當日「三大法人買賣超股數」與「收盤價」，手算 `股數 × 收盤價 / 1e8`，確認與輸出一致。

- [ ] **Step 5: 瀏覽器驗收**

在專案根目錄執行 `python -m http.server 8000`，開啟 `http://localhost:8000/web/index.html`，逐項確認：

- 泡泡圖顯示 76 個泡泡，分佈於四象限
- 切換深淺色主題，兩種模式下文字與泡泡皆清晰可辨
- 點擊泡泡展開該板塊成分股，檔數與泡泡提示一致
- 排行榜三個分頁（當日／近 5 日／近 20 日）切換後排序正確
- 縮放視窗至手機寬度（約 390px），無水平捲軸

- [ ] **Step 6: 提交**

```bash
git add tests/test_acceptance.py
git commit -m "test: 新增端到端驗收測試"
```

---

## 完成後的日常使用

```bash
# 每個交易日 18:30 後執行，更新資料
python -m pipeline.run

# 開啟頁面
python -m http.server 8000
# 瀏覽器開 http://localhost:8000/web/index.html
```

`data/raw/` 會累積原始回應快取，重跑不會重複請求交易所。要強制重抓某日，刪掉對應的快取檔即可。

## 後續可加項目（本計畫不做）

規格第 1 節列為非目標，若日後要加：

- 板塊資金輪動回放：需額外輸出 `sector_timeline.json`，前端加時間軸控制
- 外資／投信／自營商拆分：`extract` 已能取得分項欄位索引，改動集中在 `aggregate`
- 自選股：前端 `localStorage`，不需後端
- 盤中資料：需新增後端（TWSE MIS 無 CORS 標頭），且只能取得量能等代理指標，無法取得法人買賣超



