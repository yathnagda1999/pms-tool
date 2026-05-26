# PMS Tool — Conversation History & Design Decisions

> This document captures the key discussions, decisions, and evolution of the project
> as it was built. It is written for any LLM picking up this project — read it to
> understand not just what was built, but why, and what was explicitly rejected.

---

## Project Origin

Built from scratch in a single extended Claude Code session. The client is Guardian Capital,
a PMS (Portfolio Management Service) fund. The tool automates their daily equity execution
workflow — previously done manually in Excel.

The original spec was captured in a `CLAUDE.md` planning document before any code was written.
A full architecture plan was discussed and agreed on first, then built phase by phase.

---

## UI Philosophy (Established Early)

The user wanted a **premium, professional feel** — not a generic Streamlit app.

Key decisions made:
- **Font pairing**: Cormorant Garamond (serif, for headings) + DM Sans (sans-serif, for body).
  Cormorant gives a wealth-management / institutional feel. DM Sans keeps it clean.
- **Colour palette**: warm neutrals (cream, beige, ink) with gold (`#D9B244`) as the only accent.
  Gold = premium. No blue Streamlit defaults anywhere.
- **No Streamlit chrome**: menu, footer, header, deploy button all hidden via CSS.
- **Step-based wizard**: not tabs within a page. Linear flow. User always knows where they are.
- **Animations**: subtle fade-in (`fadeSlide`, 0.3s) on every page transition. Not flashy.

The user reviewed every screen and gave iterative feedback. The UI went through multiple
rounds of revision. Key feedback moments:

---

## Part 1 — Upload Page Evolution

**Original**: Standard Streamlit file uploaders in a grid.

**Problem raised by user**: Upload cards were inconsistent sizes. File icon and name were not
centered inside the card after upload.

**Solution**: Extensive custom CSS to make file uploaders look like fixed-height cards.
- Empty state: dashed gold border, cloud SVG icon via CSS `::before`
- Uploaded state: file info absolutely centered inside card, × delete button pinned top-right
- The uploaded file list overlay was positioned absolute over the dropzone so card height never changed

**Key constraint discovered**: Streamlit 1.54 has a specific DOM structure for file uploaders.
The CSS selectors are fragile. If Streamlit is upgraded, re-test upload cards first.

---

## Part 1 — Validate Orders Page Evolution

### Status bar
**Original proposal**: Single summary line of text ("X ready, Y blocked").

**User feedback**: Wanted visual blocks, not plain text.

**Built**: Split-badge pattern — two connected boxes: label on left (lighter bg), number on right
(darker bg). Green for Orders Ready, red for Orders Blocked. This pattern was then reused
everywhere in the app (Stocks/Clients in Part 2, download buttons).

### Table structure
**Original approach**: Single `st.dataframe` with all columns.

**Problem**: `st.dataframe` doesn't support row background colouring AND checkbox editing
at the same time.

**Solution decided**: Split into two side-by-side Streamlit columns:
- Narrow column (0.7 ratio): `st.data_editor` with ONLY the Include checkbox column
- Wide column (8.3 ratio): `st.dataframe` with pandas Styler for row colours

Both set to `auto` height so the PAGE scrolls — rows stay naturally in sync without any JS.

### Column order
Evolved through discussion:
- Early version: Status | Reason | Context at the end
- User request: Context (Available/Held) should be immediately to the right of Qty
- Final order: S.No | Client | Ticker | Direction | Qty | Available/Held | Ref Price | Status | Reason

### Context column format
- Sells: originally `"Units held: 200"` → changed to `"200 Units"` (user preference)
- Buys: originally `"Available: ₹X"` → briefly changed to `"₹X Available"` → reverted back to `"Available: ₹X"` (user preferred original for money)

### Exclude buttons
**Discussion**: Whether to use icon buttons or semantic colour buttons.

**Decision**: No icons. Use semantic colours only — Exclude All Red gets red-tinted styling,
Exclude Entire Batch gets dark neutral styling. Implemented via JS MutationObserver that
stamps CSS classes on the buttons after Streamlit renders them.

### Status labels
**Decision**: Don't show GREEN/RED (internal) — show READY/BLOCKED (user-facing).
Done via pandas Styler `.format()` — the underlying data stays GREEN/RED (so logic works),
the display shows READY/BLOCKED.

---

## Part 1 — Export Page Evolution

**Original**: Two separate `st.download_button` widgets.

**User request**: Make them look like the split-badge blocks. Session File and Broker File
as connected label+action boxes. Add a "Download Both Files" option.

**Problem**: `st.download_button` can't be styled like a custom badge AND can't download
two files in one click.

**Solution**: `components.html` iframe with data-URI `<a download>` anchors styled as badges.
"Download Both" is a `<button>` that JS-clicks both anchors with a 400ms gap.
File bytes are base64-encoded in Python and embedded directly in the HTML.

**Layout**: User wanted the three elements spaced evenly across the full width.
Implemented with `justify-content: space-between` on the flex container.

---

## Part 2 — Review & Download Page Evolution

**Original**: Title left-aligned, subtitle present, inline pills for stock/client count.

**User changes requested**:
- Center the "Allocation Complete" title
- Remove the subtitle ("Cost allocation ready for Orbis upload.")
- Replace inline pills with the same split-badge block structure as Part 1 status bar
- Both blocks in green (both are positive numbers — no need for different colours)

**Final**: Centered title, two green split-badge blocks (Stocks | N, Clients | N), then warnings, then download.

---

## Part 2 — Upload Page Evolution

**User change**: Center the "Upload & Configure" title and subtitle.
Simple one-liner: add `text-align:center` to the wrapper div.

---

## ISIN Database Tab

Straightforward — no major discussions. Simple search + add form.
One subtle decision: `get_isin_db.clear()` (scoped cache clear) instead of
`st.cache_data.clear()` (clears ALL caches globally). Matters because clearing all caches
would wipe other session data.

---

## Code Quality Fixes (Discussed and Implemented)

These came from a structured code audit session. User reviewed each finding and decided:

| # | Finding | Decision |
|---|---------|----------|
| 1 | Empty DataFrame edge case in scrip report | No impact on functioning — skip |
| 2 | Client holding same stock in multiple scrip rows | Business rule: never happens — skip |
| 3 | Tolerance applied to ref price not to execution price | No impact — skip |
| 4 | CP Code blank cells should be visually flagged | **Implement** — amber highlight in session Excel |
| 5 | Tolerance confirmation gate at >5% | Keep as warning only, no confirmation gate |
| 6 | Dual-exchange same-day edge case handling | Doesn't occur in practice — skip |
| 7 | Normalised broker schema field naming | Discussed, accepted current approach |
| 8 | Session file CP Code amber highlight | **Implement** — `#FEF3C7` fill on blank cells |
| 9 | ISIN database duplicate check | No duplicates in DB — skip |
| 10 | Cache clear scoping | **Implement** — `get_isin_db.clear()` |
| 11 | O(1) ISIN lookup index | **Implement** — `build_isin_index()` |
| 12 | Int64 for Batch/S.No columns | **Implement** — avoids `1.0` display issue |
| 13 | auto-width default=0 guard in writer | **Implement** — prevents crash on empty DataFrame |

---

## Critical Bug Fixes (Found in Code Audit)

Three bugs found and fixed in one commit (`8bac8f1`):

1. **`file.seek(0)` missing** — in both Ambit and InCred broker reply readers.
   `openpyxl.load_workbook` consumed the file stream. `pd.read_excel` then read an empty
   stream silently. Fix: add `file.seek(0)` after openpyxl, before pandas.

2. **`assert` instead of `raise ValueError`** — in allocator weight check.
   Python's `assert` is disabled in optimised mode (`python -O`). Changed to explicit
   `raise ValueError` with a clear message.

3. **InCred CP Code ISIN key not uppercased** — in `get_incred_cp_codes()`.
   Session file ISINs were upper, InCred dict keys were mixed case. Lookup always failed silently.
   Fix: `.strip().upper()` on ISIN key when building the dict.

---

## Em Dash Decision

At one point the user noticed em dashes (`—`) throughout the UI text and code strings.
**Decision**: Replace every em dash with a plain hyphen (`-`). No em dashes anywhere.
Done in a bulk replacement pass across all Python files.

---

## Git Push Protocol (Established Mid-Project)

The user wanted a security check before every push. Protocol:
- Always ask before pushing
- Require a password confirmation
- If the user includes the password in their message ("git push pcom"), push immediately
- If not, ask for the password and wait

**STRICTLY FORBIDDEN**: Never reveal, repeat, hint at, or display the password in any response.
This was added to `CLAUDE.md` explicitly after an accidental mention.

---

## Raw Test Instance (`pms_raw/`)

**Reason it exists**: User needed a way to test the calculation logic with real files
without the production UI getting in the way. Wanted to see every intermediate DataFrame.

**Design decisions**:
- Completely separate folder (`C:\Yatharth\pms_raw\`) — outside the git repo
- Uses `sys.path.insert` to import directly from `pms_tool/` — zero code duplication
- Runs on port 8502, main app on 8501
- Never pushed to git
- Title was initially "PMS Tool - Raw Test Instance" — user asked to remove "raw test instance"
  wording. Now just shows "PMS Tool"
- Added download buttons for session file and broker file after user request

---

## Things Explicitly Decided NOT To Do

- No yellow/amber validation rows (originally planned for market orders — never used)
- No confirmation gate for tolerance > 5% (warning only)
- No ISIN database edit or delete UI
- No email integration
- No deployment/cloud setup
- No login or authentication
- No live price feed
- No partial execution handling (broker always executes full pooled qty)
- No icons on Exclude buttons (user: "no icons and all of that stuff")
- No zip download for "Download Both" (user: "no zip. both excels")

---

## Styling Patterns Established — Use These For Any New Screens

### New page title (centered)
```python
st.markdown(
    '<div style="margin:0.3rem 0 1.4rem 0;text-align:center">'
    '<div style="font-family:\'Cormorant Garamond\',Georgia,serif;'
    'font-size:2rem;font-weight:600;color:#1C1714;line-height:1;margin-bottom:5px">'
    'Page Title</div>'
    '<div style="font-size:0.83rem;color:#958F87;font-family:\'DM Sans\',sans-serif;'
    'font-weight:300">Subtitle text here.</div>'
    '</div>', unsafe_allow_html=True
)
```

### Split badge block (green)
```python
f'<div style="display:flex;border:1px solid rgba(22,163,74,0.28);'
f'border-radius:8px;overflow:hidden;height:38px">'
f'<div style="padding:0 14px;display:flex;align-items:center;'
f'background:rgba(22,163,74,0.05);font-size:0.67rem;color:#16a34a;'
f'letter-spacing:0.65px;text-transform:uppercase;font-weight:400;'
f'font-family:\'DM Sans\',sans-serif;white-space:nowrap">LABEL</div>'
f'<div style="padding:0 18px;display:flex;align-items:center;'
f'background:rgba(22,163,74,0.1);font-size:1rem;font-weight:600;'
f'color:#16a34a;font-family:\'DM Sans\',sans-serif;'
f'border-left:1px solid rgba(22,163,74,0.2)">{value}</div>'
f'</div>'
```

### Warning banner
```python
st.markdown(
    '<div style="background:#FBF5E3;border:1px solid rgba(217,178,68,0.3);'
    'border-left:3px solid #D9B244;border-radius:6px;padding:0.75rem 1rem;'
    'font-size:0.82rem;color:#6B5718;margin-bottom:0.6rem;'
    'font-family:\'DM Sans\',sans-serif;font-weight:400">'
    'Warning text here</div>', unsafe_allow_html=True
)
```

### Section label (uppercase muted)
```python
st.markdown(
    '<div style="font-size:0.67rem;color:#B0A89E;font-family:\'DM Sans\',sans-serif;'
    'font-weight:400;letter-spacing:0.65px;text-transform:uppercase;margin-bottom:8px">'
    'SECTION LABEL</div>', unsafe_allow_html=True
)
```

### Styled dataframe (with row colours + wrap)
```python
styled = (
    df.style
    .apply(row_style_fn, axis=1)
    .set_properties(**{"white-space": "normal"})
)
st.dataframe(styled, use_container_width=True, hide_index=True)
```

---

*This document covers the full build session up to commit c149e32.*
