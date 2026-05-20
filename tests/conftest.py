"""
Shared pytest fixtures for PMS tool tests.
"""
import pytest
import pandas as pd


@pytest.fixture
def sample_research_df():
    """5-row research file with mix of BUY and SELL."""
    return pd.DataFrame({
        "S.No": [1, 2, 3, 4, 5],
        "OFIN": ["OF001", "OF002", "OF003", "OF001", "OF002"],
        "Client": ["Client A", "Client B", "Client C", "Client A", "Client B"],
        "Ticker": ["KOTAKBANK", "KOTAKBANK", "KOTAKBANK", "JIOFIN", "JIOFIN"],
        "Direction": ["BUY", "BUY", "BUY", "SELL", "SELL"],
        "Qty": [100, 200, 150, 500, 300],
        "Ref Price": [400.0, 400.0, 400.0, 230.0, 230.0],
        "Value": [40000.0, 80000.0, 60000.0, 115000.0, 69000.0],
        "CP Code": ["ORBIS0000696"] * 5,
    })


@pytest.fixture
def sample_bank_book():
    """Cash balances for 3 OFINs."""
    return {
        "OF001": 500000.0,
        "OF002": 100000.0,
        "OF003": -5000.0,
    }


@pytest.fixture
def sample_scrip_df():
    """Holdings for 3 clients — JIOFIN held, KOTAKBANK not held."""
    return pd.DataFrame({
        "OFIN": ["OF001", "OF002", "OF003"],
        "Scrip Name": ["JIOFIN", "JIOFIN", "JIOFIN"],
        "ISIN": ["INE758E01017", "INE758E01017", "INE758E01017"],
        "Quantity": [600.0, 400.0, 0.0],
    })


@pytest.fixture
def sample_isin_db():
    """Minimal ISIN database for testing."""
    return pd.DataFrame({
        "Name": ["Kotak Mahindra Bank", "Jio Financial Services"],
        "BSE Code": ["500247", "543940"],
        "NSE Code": ["KOTAKBANK", "JIOFIN"],
        "ISIN Code": ["INE237A01036", "INE758E01017"],
    })


@pytest.fixture
def sample_session_df():
    """Existing session file for batch-2 committed cash tests."""
    return pd.DataFrame({
        "S.No": [1, 2],
        "Batch": [1, 1],
        "OFIN": ["OF001", "OF002"],
        "Client": ["Client A", "Client B"],
        "Ticker": ["HDFCBANK", "HDFCBANK"],
        "ISIN": ["INE040A01034", "INE040A01034"],
        "Direction": ["BUY", "BUY"],
        "Qty": [100, 50],
        "Ref Price": [1600.0, 1600.0],
        "CP Code": ["ORBIS0000696", "ORBIS0000696"],
    })
    # OF001 committed: 100 * 1600 = 160,000
    # OF002 committed: 50  * 1600 =  80,000


@pytest.fixture
def sample_broker_normalised():
    """Normalised broker reply for KOTAKBANK BUY and JIOFIN SELL."""
    return pd.DataFrame({
        "ISIN": ["INE237A01036", "INE758E01017"],
        "Direction": ["BUY", "SELL"],
        "Exchange": ["NSE", "NSE"],
        "TradeDate": [pd.Timestamp("2026-05-18"), pd.Timestamp("2026-05-18")],
        "TotalQty": [450, 800],
        "Brokerage": [180.0, 320.0],
        "STT": [450.0, 800.0],
        "StampDuty": [67.5, 0.0],
        "SEBIChrg": [0.14, 0.25],
        "TurnoverTax": [13.77, 24.53],
        "OtherCharges": [0.0, 0.0],
        "GST": [34.92, 57.65],
        "NetAmount": [181746.33, 183797.57],
    })
