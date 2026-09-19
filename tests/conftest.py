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
