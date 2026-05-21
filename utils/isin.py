"""
ISIN database read/write/lookup utilities.
Persists to data/isin_database.csv on the server.
"""
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "isin_database.csv"

# ---------------------------------------------------------------------------
# Load (cached at the Streamlit layer via @st.cache_data)
# ---------------------------------------------------------------------------

def load_isin_database() -> pd.DataFrame:
    """Load the ISIN database CSV.

    Returns:
        pd.DataFrame: columns [Name, BSE Code, NSE Code, ISIN Code]
    """
    df = pd.read_csv(DB_PATH, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].str.strip()
    return df


# ---------------------------------------------------------------------------
# Lookup index - built once per session for O(1) lookups
# ---------------------------------------------------------------------------

def build_isin_index(db: pd.DataFrame) -> dict[str, str]:
    """Build a flat uppercase ticker → ISIN dict for O(1) lookups.

    NSE Code takes priority; BSE Code is inserted only where NSE Code is blank,
    so NSE always wins when both exist for the same ISIN.

    Args:
        db: DataFrame from load_isin_database()

    Returns:
        dict mapping uppercase ticker → ISIN Code
    """
    index: dict[str, str] = {}
    # BSE first (lower priority) - gets overwritten by NSE below
    for _, row in db.iterrows():
        bse = row["BSE Code"].strip().upper()
        if bse:
            index[bse] = row["ISIN Code"]
    # NSE second (higher priority)
    for _, row in db.iterrows():
        nse = row["NSE Code"].strip().upper()
        if nse:
            index[nse] = row["ISIN Code"]
    return index


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def lookup_isin(ticker: str, db: pd.DataFrame,
                _index: dict[str, str] | None = None) -> str | None:
    """Look up ISIN for a given ticker symbol.

    Uses pre-built O(1) index when provided; falls back to DataFrame scan.
    NSE Code match takes priority over BSE Code.

    Args:
        ticker: NSE/BSE ticker symbol (e.g. 'KOTAKBANK')
        db: ISIN database DataFrame from load_isin_database()
        _index: optional pre-built dict from build_isin_index() for O(1) lookup

    Returns:
        ISIN string if found, None otherwise
    """
    ticker_upper = ticker.strip().upper()

    if _index is not None:
        return _index.get(ticker_upper)

    # Fallback: DataFrame scan (used when index not available)
    nse_match = db[db["NSE Code"].str.upper() == ticker_upper]
    if not nse_match.empty:
        return nse_match.iloc[0]["ISIN Code"]

    bse_match = db[db["BSE Code"].str.upper() == ticker_upper]
    if not bse_match.empty:
        return bse_match.iloc[0]["ISIN Code"]

    return None


# ---------------------------------------------------------------------------
# Add new entry
# ---------------------------------------------------------------------------

def add_isin_entry(name: str, nse_code: str, bse_code: str, isin_code: str) -> None:
    """Append a new entry to the ISIN database CSV.

    Args:
        name: Company name
        nse_code: NSE ticker symbol (can be blank)
        bse_code: BSE scrip code (can be blank)
        isin_code: ISIN (required)

    Raises:
        ValueError: if isin_code is blank
    """
    if not isin_code.strip():
        raise ValueError("ISIN Code is required.")

    df = load_isin_database()
    new_row = pd.DataFrame([{
        "Name": name.strip(),
        "BSE Code": bse_code.strip(),
        "NSE Code": nse_code.strip(),
        "ISIN Code": isin_code.strip(),
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DB_PATH, index=False)
