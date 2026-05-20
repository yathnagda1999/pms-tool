"""
Input file readers for all PMS tool formats.
All functions accept a file-like object (BytesIO or UploadedFile).
All column lookups are dynamic — never hardcoded by index.
"""
from io import BytesIO

import pandas as pd
import xlrd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_ofin(series: pd.Series) -> pd.Series:
    """Cast OFIN to string, strip whitespace."""
    return series.astype(str).str.strip()


def _find_sheet(wb_sheets: list[str], expected: str) -> str:
    """Return expected sheet name or raise ValueError with helpful message."""
    if expected in wb_sheets:
        return expected
    raise ValueError(
        f"Could not find sheet '{expected}'. "
        f"Sheets found in this file: {wb_sheets}. "
        f"Please check you uploaded the correct file."
    )


def _require_columns(df: pd.DataFrame, required: list[str], source: str) -> None:
    """Raise ValueError if any required column is missing."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{source}: missing required column(s): {missing}. "
            f"Columns found: {list(df.columns)}"
        )


# ---------------------------------------------------------------------------
# Research Team File
# ---------------------------------------------------------------------------

RESEARCH_REQUIRED = ["S.No", "OFIN", "Client", "Ticker", "Direction",
                     "Qty", "Ref Price", "Value", "CP Code"]


def read_research_file(file) -> pd.DataFrame:
    """Parse the research team Excel order file.

    Args:
        file: BytesIO or Streamlit UploadedFile (.xlsx)

    Returns:
        pd.DataFrame with columns matching RESEARCH_REQUIRED.
        Direction normalised to uppercase. All strings stripped.
    """
    import openpyxl
    wb = openpyxl.load_workbook(file, data_only=True)
    _find_sheet(wb.sheetnames, "Orders")
    ws = wb["Orders"]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Research file 'Orders' sheet is empty.")

    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    data = rows[1:]
    df = pd.DataFrame(data, columns=headers)

    # Drop completely empty rows
    df = df.dropna(how="all").reset_index(drop=True)

    _require_columns(df, RESEARCH_REQUIRED, "Research file")

    # Normalise
    df["OFIN"] = _normalise_ofin(df["OFIN"])
    df["Direction"] = df["Direction"].astype(str).str.strip().str.upper()
    df["Ticker"] = df["Ticker"].astype(str).str.strip()
    df["Client"] = df["Client"].astype(str).str.strip()
    df["CP Code"] = df["CP Code"].astype(str).str.strip()
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
    df["Ref Price"] = pd.to_numeric(df["Ref Price"], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Orbis Bank Book
# ---------------------------------------------------------------------------

def read_bank_book(file) -> dict[str, float]:
    """Parse the Orbis Bank Balance Summary sheet.

    Args:
        file: BytesIO or Streamlit UploadedFile (.xlsx)

    Returns:
        dict mapping OFIN (str) → cash balance (float)
    """
    import openpyxl
    wb = openpyxl.load_workbook(file, data_only=True)
    _find_sheet(wb.sheetnames, "Bank Balance Summary")
    ws = wb["Bank Balance Summary"]

    rows = list(ws.iter_rows(values_only=True))

    # Locate header row dynamically — find row containing "OFIN Code"
    header_row_idx = None
    ofin_col = None
    balance_col = None

    for i, row in enumerate(rows):
        row_vals = [str(v).strip() if v is not None else "" for v in row]
        if "OFIN Code" in row_vals:
            header_row_idx = i
            ofin_col = row_vals.index("OFIN Code")
            balance_col = row_vals.index("Balance")
            break

    if header_row_idx is None:
        raise ValueError(
            "Bank Book: could not find header row containing 'OFIN Code'. "
            "Please check you uploaded the correct file."
        )

    # Identify "Total" marker column (same row as Balance, typically IFSC column)
    # Total rows have the word "Total" somewhere in non-OFIN, non-Balance columns
    bank_book: dict[str, float] = {}
    current_ofin: str | None = None

    for row in rows[header_row_idx + 1:]:
        row_vals = [v for v in row]

        # Check if this is a "Total" row — look for "Total" text in any cell
        is_total = any(
            str(v).strip().lower() == "total"
            for v in row_vals
            if v is not None
        )
        if is_total:
            continue

        # Skip empty rows
        if all(v is None for v in row_vals):
            continue

        # Data row: read OFIN and balance
        ofin_val = row_vals[ofin_col]
        balance_val = row_vals[balance_col]

        if ofin_val is not None and str(ofin_val).strip():
            current_ofin = str(ofin_val).strip()

        if current_ofin is not None and balance_val is not None:
            try:
                bank_book[current_ofin] = float(balance_val)
            except (ValueError, TypeError):
                pass

    return bank_book


# ---------------------------------------------------------------------------
# Orbis Scrip-wise Report (.xls)
# ---------------------------------------------------------------------------

def read_scrip_wise_report(file) -> pd.DataFrame:
    """Parse the Orbis Scripwise Clientwise Valuation Report (.xls).

    Args:
        file: BytesIO or Streamlit UploadedFile (.xls)

    Returns:
        pd.DataFrame with columns [OFIN, Scrip Name, ISIN, Quantity]
    """
    if hasattr(file, "read"):
        content = file.read()
    else:
        content = file

    wb = xlrd.open_workbook(file_contents=content)

    sheet_names = wb.sheet_names()
    if "file" not in sheet_names:
        raise ValueError(
            f"Scrip-wise Report: could not find sheet 'file'. "
            f"Sheets found: {sheet_names}. Please check the correct file."
        )

    ws = wb.sheet_by_name("file")

    # Locate header row — find row containing "Scrip Name"
    header_row_idx = None
    col_scrip = col_isin = col_client_code = col_qty = None

    for i in range(ws.nrows):
        row_vals = [str(ws.cell_value(i, j)).strip() for j in range(ws.ncols)]
        if "Scrip Name" in row_vals:
            header_row_idx = i
            col_scrip = row_vals.index("Scrip Name")
            # ISIN is labelled "Item No" in this report
            col_isin = row_vals.index("Item No") if "Item No" in row_vals else None
            col_client_code = row_vals.index("Client Code") if "Client Code" in row_vals else None
            col_qty = row_vals.index("Quantity") if "Quantity" in row_vals else None
            break

    if header_row_idx is None:
        raise ValueError(
            "Scrip-wise Report: could not find header row containing 'Scrip Name'."
        )
    if any(c is None for c in [col_isin, col_client_code, col_qty]):
        raise ValueError(
            "Scrip-wise Report: missing one of required columns "
            "'Item No', 'Client Code', 'Quantity'."
        )

    records = []
    for i in range(header_row_idx + 1, ws.nrows):
        scrip_val = str(ws.cell_value(i, col_scrip)).strip()

        # Skip "Scrip Total" rows and empty rows
        if scrip_val.lower() == "scrip total" or not scrip_val:
            continue

        # Skip if entire row is empty
        row_vals = [ws.cell_value(i, j) for j in range(ws.ncols)]
        if all(v == "" or v is None for v in row_vals):
            continue

        isin_val = str(ws.cell_value(i, col_isin)).strip()
        client_code_val = str(ws.cell_value(i, col_client_code)).strip()
        qty_val = ws.cell_value(i, col_qty)

        try:
            qty_float = float(qty_val)
        except (ValueError, TypeError):
            qty_float = 0.0

        records.append({
            "OFIN": client_code_val,
            "Scrip Name": scrip_val,
            "ISIN": isin_val,
            "Quantity": qty_float,
        })

    df = pd.DataFrame(records)
    df["OFIN"] = _normalise_ofin(df["OFIN"])
    df["Scrip Name"] = df["Scrip Name"].str.strip()
    return df


# ---------------------------------------------------------------------------
# Session File
# ---------------------------------------------------------------------------

SESSION_REQUIRED = ["S.No", "Batch", "OFIN", "Client", "Ticker",
                    "ISIN", "Direction", "Qty", "Ref Price", "CP Code"]


def read_session_file(file) -> pd.DataFrame:
    """Read an existing session file.

    Args:
        file: BytesIO or Streamlit UploadedFile (.xlsx)

    Returns:
        pd.DataFrame with SESSION_REQUIRED columns
    """
    df = pd.read_excel(file, engine="openpyxl", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    _require_columns(df, SESSION_REQUIRED, "Session file")
    df["OFIN"] = _normalise_ofin(df["OFIN"])
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
    df["Ref Price"] = pd.to_numeric(df["Ref Price"], errors="coerce")
    df["Batch"] = pd.to_numeric(df["Batch"], errors="coerce").astype(int)
    df["S.No"] = pd.to_numeric(df["S.No"], errors="coerce").astype(int)
    return df


# ---------------------------------------------------------------------------
# Broker Reply — Ambit
# ---------------------------------------------------------------------------

AMBIT_REQUIRED = ["Transaction Date", "Exchange", "ISIN No.", "Transaction Type",
                  "quantity", "Brokerage", "stt", "Stamp Duty", "SEBI Charges",
                  "Turnover Tax", "Other Charges", "GST Amount", "Net Amount"]


def read_broker_reply_ambit(file) -> pd.DataFrame:
    """Parse Ambit broker execution reply.

    Args:
        file: BytesIO or Streamlit UploadedFile (.xlsx)

    Returns:
        pd.DataFrame with normalised column names
    """
    import openpyxl
    wb = openpyxl.load_workbook(file, data_only=True)
    _find_sheet(wb.sheetnames, "Sheet1")

    df = pd.read_excel(file, sheet_name="Sheet1", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    _require_columns(df, AMBIT_REQUIRED, "Ambit broker reply")
    return df


# ---------------------------------------------------------------------------
# Broker Reply — InCred
# ---------------------------------------------------------------------------

INCRED_SHEET = "Incred_Capital_Trade_Confirmati"
INCRED_REQUIRED = ["Exchange", "ISIN No.", "Transaction Type", "Quantity",
                   "Amount", "Brokerage", "STT", "Stamp Duty", "SEBI Charges",
                   "Turnover Tax", "Other Charges", "GST Amount", "Net Amount"]


def read_broker_reply_incred(file) -> pd.DataFrame:
    """Parse InCred broker execution reply.

    Handles string-typed numeric columns and empty GST Amount.

    Args:
        file: BytesIO or Streamlit UploadedFile (.xlsx)

    Returns:
        pd.DataFrame with all numeric columns cast to float
    """
    import openpyxl
    wb = openpyxl.load_workbook(file, data_only=True)
    _find_sheet(wb.sheetnames, INCRED_SHEET)

    df = pd.read_excel(file, sheet_name=INCRED_SHEET, engine="openpyxl", dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    _require_columns(df, INCRED_REQUIRED, "InCred broker reply")

    # Cast string columns to float
    str_to_float_cols = ["Amount", "Stamp Duty", "SEBI Charges",
                         "Turnover Tax", "Other Charges"]
    for col in str_to_float_cols:
        df[col] = pd.to_numeric(df[col].str.strip(), errors="coerce").fillna(0.0)

    # GST Amount: empty string → 0.0
    df["GST Amount"] = pd.to_numeric(
        df["GST Amount"].astype(str).str.strip().replace("", "0"),
        errors="coerce"
    ).fillna(0.0)

    # Cast remaining numeric cols
    for col in ["Quantity", "Brokerage", "STT", "Net Amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
