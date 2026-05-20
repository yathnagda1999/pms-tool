"""Tests for utils/isin.py lookup logic."""
import pytest
import pandas as pd
from utils.isin import lookup_isin


@pytest.fixture
def db():
    return pd.DataFrame({
        "Name": ["Kotak Bank", "Jio Financial", "BSE Only Co"],
        "BSE Code": ["500247", "543940", "999001"],
        "NSE Code": ["KOTAKBANK", "JIOFIN", ""],
        "ISIN Code": ["INE237A01036", "INE758E01017", "INE999X01011"],
    })


def test_nse_code_lookup(db):
    assert lookup_isin("KOTAKBANK", db) == "INE237A01036"


def test_nse_code_case_insensitive(db):
    assert lookup_isin("kotakbank", db) == "INE237A01036"
    assert lookup_isin("KotakBank", db) == "INE237A01036"


def test_bse_code_fallback(db):
    # BSE Only Co has no NSE code
    assert lookup_isin("999001", db) == "INE999X01011"


def test_unknown_ticker_returns_none(db):
    assert lookup_isin("UNKNOWN", db) is None


def test_strips_whitespace(db):
    assert lookup_isin("  JIOFIN  ", db) == "INE758E01017"
