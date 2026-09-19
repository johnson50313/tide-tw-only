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
