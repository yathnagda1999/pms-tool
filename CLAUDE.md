# PMS Execution Semi-Automation Tool — Project Rules

## Git Push Protocol
- **Always ask before pushing to GitHub** — never push without explicit user confirmation.
- **Password required**: Before every `git push`, ask the user for the push password.
- **Shortcut**: If the user's message contains the password, the password is already confirmed — push immediately without asking.
- **Without shortcut**: Ask "Please confirm with the push password before I push." and wait for the user to supply it.
- Do not push under any circumstances until the password is confirmed.
- **STRICTLY FORBIDDEN**: Never reveal, repeat, hint at, or display the push password in any response, message, or file. Not even as an example.

## What this project is
Two-part Python/Streamlit tool for Guardian Capital's PMS equity order execution workflow. No login, no database, no server. Files in → processed files out. All processing in memory. Single exception: `data/isin_database.csv` persists on server.

## Tech stack
- **UI**: Streamlit (three tabs: Part 1, Part 2, ISIN Database)
- **Processing**: Python 3.11+, pandas, openpyxl, xlrd
- **Output**: Excel (.xlsx) via openpyxl

## Project structure
```
pms_tool/
├── app.py                  # Streamlit entry — three tabs
├── data/isin_database.csv  # Name | BSE Code | NSE Code | ISIN Code
├── part1/
│   ├── validator.py        # Sell/buy validation
│   ├── broker_file.py      # Broker file generator
│   └── session.py          # Session file generator
├── part2/
│   ├── parser.py           # Ambit + InCred broker reply parsers
│   ├── matcher.py          # Match broker reply to session file
│   └── allocator.py        # Weight calc + cost split
├── utils/
│   ├── reader.py           # All input file readers
│   ├── writer.py           # Allocation file writer
│   └── isin.py             # ISIN database read/write/lookup
└── tests/test_*.py
```

## Coding conventions
- Functions over classes unless state is clearly needed
- Every function has a docstring with input/output types
- Return DataFrames from processing functions — never write to disk
- Raise ValueError with clear messages for bad input
- No print statements — use st.error / st.warning / st.success

---

## Input file specs

### Research Team File (Part 1 — mandatory)
Sheet: `Orders` | Columns: `S.No | OFIN | Client | Ticker | Direction | Qty | Ref Price | Value | CP Code`
- Direction: case-insensitive, normalise to uppercase
- Ref Price: always present. Market orders are edge case only
- Value: informational only — do not use for validation
- CP Code: if blank → do not block. Highlight in session file, ask ops to fill before Part 2

### Orbis Bank Book (Part 1 — mandatory)
Sheet: `Bank Balance Summary` | Locate all columns by header name — never hardcode index
- Skip title rows. Header contains: `OFIN Code`, `Balance`
- 2 rows per client: Row 1 = OFIN + Balance. Row 2 = "Total" in IFSC col → skip
- One OFIN = one bank account always. Balances can be negative.

### Orbis Scrip-wise Report (Part 1 — mandatory)
Format: `.xls` (use xlrd) | Sheet: `file` | Locate columns by header name
- Header contains: `Scrip Name`, `Item No` (=ISIN), `Client Code` (=OFIN), `Quantity`
- Skip rows where Scrip Name = `"Scrip Total"` or row is empty
- Scrip Name matches NSE ticker exactly. ISIN repeats on every client row.

### Session File (Part 1 output → Part 2 input)
Columns: `S.No | Batch | OFIN | Client | Ticker | ISIN | Direction | Qty | Ref Price | CP Code`
- Batch = 1 for first run of day, increments per subsequent batch
- ISIN: from scrip-wise report or ISIN database lookup

### Broker Reply — Ambit (Part 2 — mandatory if Ambit selected)
Sheet: `Sheet1` | Locate columns by header name
Key columns: `Transaction Date | Exchange | NSE Symbol | BSE Scrip Code | ISIN No. | Transaction Type | quantity | Brokerage | stt | Stamp Duty | SEBI Charges | Turnover Tax | Other Charges | GST Amount | Net Amount`
- Trade date: from `Transaction Date`. CP Code: from session file.

### Broker Reply — InCred (Part 2 — mandatory if InCred selected)
Sheet: `Incred_Capital_Trade_Confirmati` | Locate columns by header name
Key columns: `Exchange | ISIN No. | Transaction Type | Quantity | Amount | Brokerage | STT | Stamp Duty | SEBI Charges | Turnover Tax | Other Charges | GST Amount | Net Amount | CP CODE`
- Trade date: today's date. CP Code: from `CP CODE` col in reply.
- Type casting: `Amount`, `Stamp Duty`, `SEBI Charges`, `Turnover Tax`, `Other Charges` → float. `GST Amount` empty string → 0.0

---

## ISIN Database (`data/isin_database.csv`)
5,324 listed companies. Zero blank ISINs. Loaded at startup.
- Lookup: NSE Code (case-insensitive) → ISIN. BSE Code as fallback.
- New entry via UI → written to CSV immediately (persistent)
- Delistings: research team edits CSV directly (out of scope)

**ISIN lookup priority (Part 1):**
1. Scrip-wise report (Ticker → Scrip Name, case-insensitive)
2. ISIN database (Ticker → NSE Code → BSE Code fallback)

---

## Core business logic — never break these
1. **Sell**: `units_held >= qty_ordered` → green. Else red.
2. **Buy**: `(bank_balance − committed_cash) >= qty × ref_price × (1 + tolerance/100)` → green. Else red.
3. **No partial executions** — broker executed qty always = session file total for that scrip.
4. **Pending sells** from existing session file: do not deduct from available units (treated as cancelled).
5. **Weight** = `client_qty / total_qty` per ISIN+Direction. Verify sum ≈ 1.0 with `math.isclose()`.
6. **Cost split**: `client_share = weight × broker_total` for every charge column.
7. **Last client per scrip** gets residual for every charge column: `broker_total − sum(others)`. Full precision.
8. **InputNetRate** = `InputNetAmount / Input Quantity`. Full precision.
9. **CP Code**: session file per row. InCred: use broker reply value if session file blank.
10. **Settlement No**: always blank. Out of scope.
11. **Same stock NSE+BSE same day** (rare): two independent executions, separate weight calculations.
12. **Tolerance > 5%** → confirmation prompt before proceeding.
13. **Rounding**: 2 decimal places on all charges. Exception: last client residual → full precision.

## Batch / append logic
- Fresh run: Batch = 1. Second batch: upload existing session file → append, Batch = max + 1.
- Committed cash (for buy validation) = sum(Qty × Ref Price) for BUY rows in existing session file, grouped by OFIN.

## Validation UI
- **Green** ✅: passes all checks — included by default
- **Red** ❌: fails — excluded by default, checkbox disabled
- No yellow — ref price always present
- Summary bar: `X ready | Y blocked`
- Buttons: `Exclude All Red` | `Exclude Entire Batch`
- Generate disabled if: any red row still included OR zero rows included
- Table columns: `Exclude ☑ | S.No | Client | Ticker | Direction | Qty | Ref Price | Status | Reason | Units Held / Available Cash`

## Orbis allocation output — exact column order
`S.No | Client Name | CustomerNo | TradeDate | Exchange Type | Settlement No | ISIN No | Buy/Sell | Input Quantity | InputBrokerage | InputSTT | InputStampDuty | InputSEBIChrg | InputTurnOver | InputOtherCharges | InputGST | InputNetAmount | InputNetRate | CP CODE`

## Broker file output — exact column order
`Ticker | Direction | Total Qty | Ref Price`

---

## Error handling
- Sheet not found → `st.error("Could not find sheet '[name]'. Found: [list].")` — stop
- Required column missing → `st.error` with column name — stop
- OFIN not in bank book or scrip-wise → red row with specific message
- Broker reply scrip not in session file → warning, do not fail
- Session file scrip not in broker reply → show as "not executed"
- All column lookups: by header name dynamically — never hardcode index
- OFIN: always cast to string, strip whitespace before matching
- Ticker matching: always case-insensitive, stripped

## Testing
- Unit test every processing function with sample DataFrames
- Edge cases: all sells, all buys, mixed, negative balance, client not found
- Allocation weights sum ≈ 1.0 for every scrip
- Last-client residual correct for each charge column
- Ambit and InCred parsers independently
- Batch append: committed cash deduction, batch numbering
- ISIN lookup: scrip-wise hit, database hit, BSE fallback
- pytest fixtures for sample data

## What NOT to build
No login, no email, no live price fetch, no cloud integrations, no deployment logic, no ISIN database deletion/edit UI
