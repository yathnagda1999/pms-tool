"""
Broker reply parsers for Ambit and InCred.
Both parsers normalise output to the same internal schema.
"""
from datetime import date

import pandas as pd

from utils.reader import read_broker_reply_ambit, read_broker_reply_incred

# Unified internal schema after normalisation
NORMALISED_COLUMNS = [
    "ISIN", "Direction", "Exchange", "TradeDate",
    "TotalQty", "Brokerage", "STT", "StampDuty",
    "SEBIChrg", "TurnoverTax", "OtherCharges", "GST", "NetAmount",
]


def parse_ambit_reply(file) -> pd.DataFrame:
    """Parse Ambit broker reply and normalise to internal schema.

    Args:
        file: BytesIO or Streamlit UploadedFile (.xlsx)

    Returns:
        pd.DataFrame with NORMALISED_COLUMNS
    """
    df = read_broker_reply_ambit(file)

    normalised = pd.DataFrame({
        "ISIN": df["ISIN No."].astype(str).str.strip(),
        "Direction": df["Transaction Type"].astype(str).str.strip().str.upper(),
        "Exchange": df["Exchange"].astype(str).str.strip().str.upper(),
        "TradeDate": pd.to_datetime(df["Transaction Date"], dayfirst=True, errors="coerce"),
        "TotalQty": pd.to_numeric(df["quantity"], errors="coerce"),
        "Brokerage": pd.to_numeric(df["Brokerage"], errors="coerce").fillna(0.0),
        "STT": pd.to_numeric(df["stt"], errors="coerce").fillna(0.0),
        "StampDuty": pd.to_numeric(df["Stamp Duty"], errors="coerce").fillna(0.0),
        "SEBIChrg": pd.to_numeric(df["SEBI Charges"], errors="coerce").fillna(0.0),
        "TurnoverTax": pd.to_numeric(df["Turnover Tax"], errors="coerce").fillna(0.0),
        "OtherCharges": pd.to_numeric(df["Other Charges"], errors="coerce").fillna(0.0),
        "GST": pd.to_numeric(df["GST Amount"], errors="coerce").fillna(0.0),
        "NetAmount": pd.to_numeric(df["Net Amount"], errors="coerce"),
    })

    return normalised[NORMALISED_COLUMNS]


def parse_incred_reply(file) -> pd.DataFrame:
    """Parse InCred broker reply and normalise to internal schema.

    Trade date is today's date (InCred reply has no date column).
    CP Code is read from the reply and stored separately — call get_incred_cp_codes() if needed.

    Args:
        file: BytesIO or Streamlit UploadedFile (.xlsx)

    Returns:
        pd.DataFrame with NORMALISED_COLUMNS
    """
    df = read_broker_reply_incred(file)

    normalised = pd.DataFrame({
        "ISIN": df["ISIN No."].astype(str).str.strip(),
        "Direction": df["Transaction Type"].astype(str).str.strip().str.upper(),
        "Exchange": df["Exchange"].astype(str).str.strip().str.upper(),
        "TradeDate": pd.Timestamp(date.today()),
        "TotalQty": pd.to_numeric(df["Quantity"], errors="coerce"),
        "Brokerage": pd.to_numeric(df["Brokerage"], errors="coerce").fillna(0.0),
        "STT": pd.to_numeric(df["STT"], errors="coerce").fillna(0.0),
        "StampDuty": df["Stamp Duty"].astype(float),
        "SEBIChrg": df["SEBI Charges"].astype(float),
        "TurnoverTax": df["Turnover Tax"].astype(float),
        "OtherCharges": df["Other Charges"].astype(float),
        "GST": df["GST Amount"].astype(float),
        "NetAmount": pd.to_numeric(df["Net Amount"], errors="coerce"),
    })

    return normalised[NORMALISED_COLUMNS]


def get_incred_cp_codes(file) -> dict[str, str]:
    """Extract ISIN → CP Code mapping from InCred reply.

    Used in allocator to source CP Code per row when session file CP Code is blank.

    Args:
        file: BytesIO or Streamlit UploadedFile (.xlsx)

    Returns:
        dict mapping ISIN → CP Code string
    """
    df = read_broker_reply_incred(file)
    if "CP CODE" not in df.columns:
        return {}
    result = {}
    for _, row in df.iterrows():
        isin = str(row["ISIN No."]).strip().upper()  # normalise to uppercase for consistent lookup
        cp = str(row.get("CP CODE", "")).strip()
        if isin and cp:
            result[isin] = cp
    return result
