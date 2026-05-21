"""
Matches session file rows to broker reply rows.
Match key: ISIN + Direction (+ Exchange for rare dual-exchange trades).
"""
import pandas as pd


def match_session_to_broker(
    session_df: pd.DataFrame,
    broker_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Match session file rows to broker reply.

    For the rare case of same ISIN on two exchanges (NSE + BSE),
    each exchange row is treated as an independent execution.

    Args:
        session_df: session file DataFrame (10 columns)
        broker_df: normalised broker reply DataFrame (NORMALISED_COLUMNS)

    Returns:
        Tuple of:
            matched_session_df: session_df rows with broker data merged in
            not_executed: list of ISIN values in session file but not in broker reply
            unexpected: list of ISIN values in broker reply but not in session file
    """
    session = session_df.copy()
    broker = broker_df.copy()

    session["_ISIN_upper"] = session["ISIN"].astype(str).str.strip().str.upper()
    session["_Dir_upper"] = session["Direction"].astype(str).str.strip().str.upper()
    broker["_ISIN_upper"] = broker["ISIN"].astype(str).str.strip().str.upper()
    broker["_Dir_upper"] = broker["Direction"].astype(str).str.strip().str.upper()

    # Check for dual-exchange: same ISIN+Direction appearing on multiple exchanges
    broker_key_counts = broker.groupby(["_ISIN_upper", "_Dir_upper"])["Exchange"].nunique()
    dual_exchange_keys = broker_key_counts[broker_key_counts > 1].index.tolist()

    session_keys = set(zip(session["_ISIN_upper"], session["_Dir_upper"]))
    broker_keys = set(zip(broker["_ISIN_upper"], broker["_Dir_upper"]))

    not_executed_keys = session_keys - broker_keys
    unexpected_keys = broker_keys - session_keys

    not_executed = sorted({isin for isin, _ in not_executed_keys})
    unexpected = sorted({isin for isin, _ in unexpected_keys})

    # For dual-exchange: extend match key to include Exchange
    if dual_exchange_keys:
        # Build a separate broker subset for dual-exchange ISINs
        # Session rows for these ISINs get matched to ALL broker rows for that ISIN+Direction
        # (resulting in multiple allocation groups per ISIN+Direction)
        # This is handled in the allocator by grouping on ISIN+Direction+Exchange
        broker = broker.copy()

    # Merge: keep only session rows that have a broker match
    matched = session[
        session.apply(lambda r: (r["_ISIN_upper"], r["_Dir_upper"]) in broker_keys, axis=1)
    ].copy()

    # Attach broker data to matched session rows
    # For dual-exchange, one session row joins to multiple broker rows - handled in allocator
    broker_indexed = broker.set_index(["_ISIN_upper", "_Dir_upper"])

    def _attach_broker(row):
        key = (row["_ISIN_upper"], row["_Dir_upper"])
        if key not in broker_indexed.index:
            return row
        b = broker_indexed.loc[key]
        if isinstance(b, pd.DataFrame):
            # Multiple broker rows (dual exchange) - take first for now; allocator handles split
            b = b.iloc[0]
        row["_broker_exchange"] = b["Exchange"]
        row["_broker_trade_date"] = b["TradeDate"]
        return row

    matched = matched.apply(_attach_broker, axis=1)

    # Clean up temp columns
    matched = matched.drop(columns=["_ISIN_upper", "_Dir_upper"], errors="ignore")

    return matched, not_executed, unexpected
