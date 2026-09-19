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
