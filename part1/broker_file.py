"""
Broker file generator for Part 1.
Aggregates client orders into a pooled broker instruction file.
"""
import pandas as pd


def build_broker_file(included_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate included client orders into a pooled broker file.

    Groups by Ticker + Direction, sums Qty.
    Ref Price is the same for all clients per Ticker+Direction (guaranteed by research team).

    Args:
        included_df: validated DataFrame filtered to included rows only.

    Returns:
        pd.DataFrame with columns [Ticker, Direction, Total Qty, Ref Price]
    """
    grouped = (
        included_df
        .groupby(["Ticker", "Direction"], sort=False)
        .agg(
            **{
                "Total Qty": ("Qty", "sum"),
                "Ref Price": ("Ref Price", "first"),
            }
        )
        .reset_index()
    )

    return grouped[["Ticker", "Direction", "Total Qty", "Ref Price"]]
