# SENSEX OI Change — CE & PE 6-Strike Dashboard

A local Streamlit dashboard using DhanHQ Option Chain API, Plotly, and SQLite snapshots.

## Features
- SENSEX BSE option-chain polling, selected expiry and 3 CE + 3 PE strikes
- Plotly time-series chart with unified hover
- Persistent intraday snapshots in SQLite
- CSV export and latest OI metrics
- Dhan token stored in local `.env` or entered into the sidebar as a password field

## Important API notes
- Dhan API response schemas and security IDs can change. Verify the current official DhanHQ documentation before live use.
- Set `DHAN_SENSEX_UNDERLYING_SECURITY_ID` from the current Dhan instrument master. This app deliberately does not hard-code a potentially stale security ID.
- The underlying is an index, so the request uses `UnderlyingSeg: IDX_I` as shown in Dhan documentation. Confirm the SENSEX index security ID from the current instrument master.
- The Option Chain endpoint may have a minimum request interval/rate limit. This app polls once per selected refresh interval (default 60 seconds).
- First observed OI for each strike is the baseline, so the chart shows change since this app first recorded it, not necessarily official day-open OI. Start it before or at market open for a closer all-day view.
- For robust production use, run a background collector during market hours rather than relying on a browser tab remaining open.

## Install (Windows PowerShell)
1. Install Python 3.10+.
2. Extract the ZIP and open PowerShell in the project folder.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`, then edit `.env` locally:
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```
5. Add your Dhan client ID, access token, and current SENSEX underlying security ID.
6. Start the app:
   ```powershell
   streamlit run app.py
   ```
7. In the sidebar, select expiry, strikes, and enable auto-refresh.

## Data and security
- `.env` and the SQLite database are excluded from Git via `.gitignore`.
- Never paste credentials into chat, upload `.env`, or publish the project with a real token.
- Revoke/rotate the token if it is accidentally exposed.
- The SQLite database is local and persists between app restarts. It is not encrypted; protect your Windows user account and disk.
