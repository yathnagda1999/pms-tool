"""
Excel file writers — produce bytes for Streamlit download buttons.
"""
from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, numbers
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# Generic writer
# ---------------------------------------------------------------------------

def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    """Write a DataFrame to Excel and return as bytes.

    Args:
        df: DataFrame to write
        sheet_name: target sheet name

    Returns:
        bytes suitable for st.download_button
    """
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Allocation file writer — formatted
# ---------------------------------------------------------------------------

CURRENCY_COLS = {
    "InputBrokerage", "InputSTT", "InputStampDuty", "InputSEBIChrg",
    "InputTurnOver", "InputOtherCharges", "InputGST",
    "InputNetAmount", "InputNetRate",
}

HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)


def write_allocation_file(allocation_df: pd.DataFrame) -> bytes:
    """Write the Orbis allocation file with formatting.

    - Bold white-on-blue header row
    - Number format '0.00' on all charge and net columns
    - Date format on TradeDate
    - Auto-width columns
    - Settlement No always blank

    Args:
        allocation_df: 19-column allocation DataFrame from allocator

    Returns:
        bytes suitable for st.download_button
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Allocation"

    cols = list(allocation_df.columns)

    # Header row
    for col_idx, col_name in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Data rows
    for row_idx, (_, row) in enumerate(allocation_df.iterrows(), start=2):
        for col_idx, col_name in enumerate(cols, start=1):
            val = row[col_name]
            cell = ws.cell(row=row_idx, column=col_idx, value=val)

            if col_name in CURRENCY_COLS and val is not None:
                cell.number_format = "0.00"
            elif col_name == "TradeDate" and val is not None:
                cell.number_format = "DD-MMM-YYYY"
            elif col_name == "Settlement No":
                cell.value = None  # always blank

    # Auto-width
    for col_idx, col_name in enumerate(cols, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = max(
            len(str(col_name)),
            *[
                len(str(ws.cell(row=r, column=col_idx).value or ""))
                for r in range(2, ws.max_row + 1)
            ],
        )
        ws.column_dimensions[col_letter].width = min(max_len + 2, 30)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
