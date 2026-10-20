import os
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from dhan_client import DhanClient
from storage import init_db, save_snapshot, load_snapshots, clear_today

load_dotenv()
TZ = ZoneInfo("Asia/Kolkata")

st.set_page_config(page_title="SENSEX OI Change Dashboard", page_icon="📊", layout="wide")
init_db()

st.title("📊 SENSEX OI Change — CE & PE (6 Strikes)")
st.caption("DhanHQ API · Intraday snapshots · India time (IST)")

with st.sidebar:
    st.header("Connection")
    client_id_input = st.text_input("Dhan Client ID", value=os.getenv("DHAN_CLIENT_ID", ""), type="default")
    access_token_input = st.text_input("Dhan Access Token", value=os.getenv("DHAN_ACCESS_TOKEN", ""), type="password")
    st.caption("Credentials are used only by this local app. Prefer setting them in .env.")
    st.divider()
    st.header("Option setup")
    expiry = st.date_input("Expiry date", value=date.today(), help="Choose the actual SENSEX option expiry shown in Dhan.")
    default_strikes = [73800, 73900, 74000]
    st.markdown("**CE strikes**")
    ce1 = st.number_input("CE Strike 1", min_value=1, value=73800, step=100)
    ce2 = st.number_input("CE Strike 2", min_value=1, value=73900, step=100)
    ce3 = st.number_input("CE Strike 3", min_value=1, value=74000, step=100)
    st.markdown("**PE strikes**")
    pe1 = st.number_input("PE Strike 1", min_value=1, value=73800, step=100)
    pe2 = st.number_input("PE Strike 2", min_value=1, value=73900, step=100)
    pe3 = st.number_input("PE Strike 3", min_value=1, value=74000, step=100)
    refresh_seconds = st.selectbox("Refresh interval", [60, 120, 180, 300], index=0, format_func=lambda x: f"{x // 60} minute(s)")
    run_live = st.toggle("Enable auto-refresh polling", value=False)
    st.caption("Polling calls the option-chain endpoint once per refresh. Do not run multiple copies with the same token.")
    st.divider()
    if st.button("Clear today's saved snapshots", type="secondary"):
        clear_today()
        st.success("Today's local snapshots cleared.")

if not client_id_input or not access_token_input:
    st.warning("Enter your Dhan Client ID and Access Token in the sidebar, or add them to the .env file. The chart will use saved data until then.")
    client = None
else:
    client = DhanClient(client_id_input.strip(), access_token_input.strip())

strikes = {
    ("CE", int(ce1)), ("CE", int(ce2)), ("CE", int(ce3)),
    ("PE", int(pe1)), ("PE", int(pe2)), ("PE", int(pe3)),
}
if len(strikes) < 6:
    st.info("Some CE/PE strike pairs repeat. That's allowed, but duplicate CE or PE strike selections will be deduplicated.")

col1, col2, col3 = st.columns(3)
col1.metric("Selected CE strikes", ", ".join(map(str, sorted({int(ce1), int(ce2), int(ce3)}))))
col2.metric("Selected PE strikes", ", ".join(map(str, sorted({int(pe1), int(pe2), int(pe3)}))))
col3.metric("Selected expiry", expiry.strftime("%d %b %Y"))

# One snapshot per polling run; the app stores absolute OI plus OI change versus first
# observed point of the current trading date, so the chart remains meaningful after reruns.
fetch_error = None
if client is not None and run_live:
    try:
        now = datetime.now(TZ)
        payload = client.option_chain(expiry.isoformat())
        rows = client.extract_selected(payload, strikes)
        if rows:
            save_snapshot(now, expiry.isoformat(), rows)
            st.success(f"Snapshot saved at {now.strftime('%H:%M:%S')} IST · {len(rows)} selected option rows")
        else:
            st.warning("API returned no rows matching the selected strikes. Check expiry/strike values and API response.")
    except Exception as e:
        fetch_error = str(e)
        st.error(f"API fetch failed: {fetch_error}")

df = load_snapshots(expiry.isoformat())
if not df.empty:
    # Restrict view to currently selected strikes; keep older history if the selection changes.
    wanted = {(side, strike) for side, strike in strikes}
    df = df[df.apply(lambda r: (r["option_type"], int(r["strike"])) in wanted, axis=1)].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["series"] = df["option_type"] + " " + df["strike"].astype(int).astype(str)
    df = df.sort_values("timestamp")
    # Change from first recorded OI for each strike on the selected expiry.
    df["oi_change"] = df.groupby(["option_type", "strike"])["open_interest"].transform(lambda s: s - s.iloc[0])
    df["time_label"] = df["timestamp"].dt.strftime("%H:%M:%S")

    latest = df.sort_values("timestamp").groupby(["option_type", "strike"], as_index=False).tail(1)
    mcols = st.columns(6)
    for i, (_, r) in enumerate(latest.sort_values(["option_type", "strike"]).iterrows()):
        mcols[i % 6].metric(f'{r["option_type"]} {int(r["strike"])}', f'{int(r["open_interest"]):,}', f'{int(r["oi_change"]):+,} OI')

    fig = px.line(
        df, x="timestamp", y="oi_change", color="series", markers=False,
        title="OI Change — CE & PE (6 Strikes Comparison)",
        labels={"timestamp": "Time (IST)", "oi_change": "OI Change", "series": "Strike"},
        hover_data={"open_interest": ":,", "strike": True, "option_type": True, "time_label": True}
    )
    fig.update_layout(hovermode="x unified", legend_title_text="", height=540, margin=dict(l=10, r=10, t=60, b=10))
    fig.update_xaxes(tickformat="%H:%M", showgrid=True)
    fig.update_yaxes(zeroline=True, zerolinewidth=1)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Snapshot data"):
        st.dataframe(df[["timestamp", "option_type", "strike", "open_interest", "oi_change"]].sort_values("timestamp", ascending=False), use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download selected data as CSV", csv, file_name=f"sensex_oi_{expiry.isoformat()}.csv", mime="text/csv")
else:
    st.info("No saved snapshots yet. Turn on auto-refresh polling and keep this page open during market hours. The first snapshot establishes the baseline, so its OI Change is zero.")

if run_live:
    st.caption(f"Auto-refresh is enabled. Streamlit reruns every {refresh_seconds} seconds; the next rerun will fetch another snapshot.")
    time.sleep(refresh_seconds)
    st.rerun()
else:
    st.caption("Auto-refresh is off. Enable it in the sidebar to poll Dhan every minute. The browser/app must remain open.")
