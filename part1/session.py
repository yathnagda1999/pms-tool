"""
Session file generator for Part 1.
Builds or appends to the cumulative session file for the day.
"""
import pandas as pd

SESSION_COLUMNS = ["S.No", "Batch", "OFIN", "Client", "Ticker",
                   "ISIN", "Direction", "Qty", "Ref Price", "CP Code"]


def build_session_file(
    included_df: pd.DataFrame,
    existing_session_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build or append to the session file.

    Args:
        included_df: validated DataFrame filtered to included rows only.
                     Must contain research file columns + ISIN column.
        existing_session_df: existing session file to append to, or None for fresh start.

    Returns:
        pd.DataFrame with SESSION_COLUMNS.
        CP Code blank cells are preserved (highlighted in UI, not blocked).
    """
    # Determine batch number
    if existing_session_df is not None and not existing_session_df.empty:
        batch_num = int(existing_session_df["Batch"].max()) + 1
    else:
        batch_num = 1

    new_rows = pd.DataFrame({
        "S.No": included_df["S.No"].values,
        "Batch": batch_num,
        "OFIN": included_df["OFIN"].values,
        "Client": included_df["Client"].values,
        "Ticker": included_df["Ticker"].values,
        "ISIN": included_df["ISIN"].values,
        "Direction": included_df["Direction"].values,
        "Qty": included_df["Qty"].values,
        "Ref Price": included_df["Ref Price"].values,
        "CP Code": included_df["CP Code"].values,
    })

    if existing_session_df is not None and not existing_session_df.empty:
        session_df = pd.concat(
            [existing_session_df[SESSION_COLUMNS], new_rows],
            ignore_index=True,
        )
    else:
        session_df = new_rows.reset_index(drop=True)

    return session_df[SESSION_COLUMNS]
