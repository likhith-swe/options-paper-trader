"""
Interactive Paper Trading Web Dashboard
Built with Streamlit & Plotly: Visualizes portfolio equity curve, live trades, and strategy metrics.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.ledger import LedgerDB

st.set_page_config(
    page_title="Paper Trading Command Center | ₹10 Lakhs Portfolio",
    page_icon="📈",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 15px;
        border-left: 4px solid #3B82F6;
    }
    .gain-text { color: #22C55E; font-weight: bold; }
    .loss-text { color: #EF4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

ledger = LedgerDB()
account = ledger.get_account()
snapshots = ledger.get_all_snapshots()

st.title("📈 Quantitative Options Paper Trading Command Center")
st.caption("Active Strategies: NIFTY 50 (Quantman 1165) & SENSEX (1lyAlgos Momentum Catcher) | Capital: ₹10,00,000")

# Top KPI Metric Cards
col1, col2, col3, col4, col5 = st.columns(5)

total_cash = account.get("cash_balance", 1000000.0)
allocated = account.get("allocated_margin", 0.0)
total_equity = total_cash + allocated
initial_cap = account.get("initial_balance", 1000000.0)
realized_pnl = account.get("realized_pnl", 0.0)
total_charges = account.get("total_charges", 0.0)
total_net = realized_pnl - total_charges
roi_pct = (total_net / initial_cap) * 100.0

col1.metric("Total Portfolio Equity", f"₹ {total_equity:,.2f}", f"{roi_pct:+.2f}% ROI")
col2.metric("Available Cash Balance", f"₹ {total_cash:,.2f}", "Unallocated")
col3.metric("Allocated Active Margin", f"₹ {allocated:,.2f}", "In Trades")
col4.metric("Cumulative Net P&L", f"₹ {total_net:+,.2f}", f"Gross: ₹{realized_pnl:+,.2f}")
col5.metric("Total Brokerage & Taxes", f"₹ {total_charges:,.2f}", "Friction")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 Equity Curve & Daily Snapshots", "📜 Today's Trade Journal", "⚙️ Strategy Performance Analytics"])

# TAB 1: Equity Curve & Snapshots
with tab1:
    st.subheader("Portfolio Equity Growth & Daily P&L Trajectory")
    if snapshots:
        df_snap = pd.DataFrame(snapshots)
        df_snap["Date"] = pd.to_datetime(df_snap["snapshot_date"])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_snap["Date"], y=df_snap["closing_balance"],
            mode="lines+markers",
            name="Portfolio Balance (₹)",
            line=dict(color="#3B82F6", width=3),
            marker=dict(size=8, color="#60A5FA")
        ))
        fig.update_layout(
            title="Equity Curve Over Time (Starting Capital: ₹10,00,000)",
            xaxis_title="Date",
            yaxis_title="Total Portfolio Value (₹)",
            template="plotly_dark",
            height=380
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Daily Performance Log")
        st.dataframe(df_snap[[
            "snapshot_date", "opening_balance", "closing_balance",
            "daily_gross_pnl", "daily_charges", "daily_net_pnl", "roi_pct",
            "total_trades", "winning_trades", "losing_trades"
        ]].rename(columns={
            "snapshot_date": "Date",
            "opening_balance": "Open Bal (₹)",
            "closing_balance": "Close Bal (₹)",
            "daily_gross_pnl": "Gross P&L (₹)",
            "daily_charges": "Taxes & Fees (₹)",
            "daily_net_pnl": "Net P&L (₹)",
            "roi_pct": "Daily ROI %",
            "total_trades": "Trades",
            "winning_trades": "Wins",
            "losing_trades": "Losses"
        }), hide_index=True)
    else:
        st.info("No daily snapshots recorded yet. Run today's trading session to initialize the equity curve.")

# TAB 2: Today's Trades
with tab2:
    st.subheader("Executed Trade Log")
    today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_trades = ledger.get_trades_for_date(today_str)
    
    if not today_trades:
        # Check all trades
        with ledger._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trades ORDER BY entry_time DESC LIMIT 50")
            all_trades = [dict(r) for r in cur.fetchall()]
        today_trades = all_trades

    if today_trades:
        df_trades = pd.DataFrame(today_trades)
        st.dataframe(df_trades[[
            "trade_date", "strategy", "instrument", "option_type", "quantity",
            "entry_time", "entry_price", "exit_time", "exit_price",
            "exit_reason", "gross_pnl", "brokerage", "taxes", "net_pnl", "status"
        ]].rename(columns={
            "trade_date": "Date",
            "strategy": "Strategy",
            "instrument": "Contract",
            "option_type": "Type",
            "quantity": "Qty",
            "entry_time": "Entry Time",
            "entry_price": "Buy Px",
            "exit_time": "Exit Time",
            "exit_price": "Sell Px",
            "exit_reason": "Exit Reason",
            "gross_pnl": "Gross (₹)",
            "brokerage": "Brok (₹)",
            "taxes": "Tax (₹)",
            "net_pnl": "Net P&L (₹)",
            "status": "Status"
        }), hide_index=True)
    else:
        st.info("No trades executed yet.")

# TAB 3: Strategy Analytics
with tab3:
    st.subheader("Strategy Level Attribution & Metrics")
    with ledger._get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM trades WHERE status = 'CLOSED'")
        closed = [dict(r) for r in cur.fetchall()]

    if closed:
        df_c = pd.DataFrame(closed)
        col_s1, col_s2 = st.columns(2)
        
        # Nifty Analytics
        df_n = df_c[df_c["strategy"] == "NIFTY_1165"]
        with col_s1:
            st.markdown("### NIFTY 50 (Quantman 1165)")
            if len(df_n) > 0:
                n_wins = (df_n["net_pnl"] > 0).sum()
                st.write(f"• Total Trades: **{len(df_n)}**")
                st.write(f"• Win Rate: **{n_wins / len(df_n) * 100:.1f}%** ({n_wins} Wins)")
                st.write(f"• Net P&L: **₹ {df_n['net_pnl'].sum():+,.2f}**")
                st.write(f"• Total Costs: **₹ {df_n['brokerage'].sum() + df_n['taxes'].sum():,.2f}**")
            else:
                st.write("No NIFTY trades recorded yet.")

        # Sensex Analytics
        df_s = df_c[df_c["strategy"] == "SENSEX_1LY"]
        with col_s2:
            st.markdown("### SENSEX (1lyAlgos Momentum)")
            if len(df_s) > 0:
                s_wins = (df_s["net_pnl"] > 0).sum()
                st.write(f"• Total Trades: **{len(df_s)}**")
                st.write(f"• Win Rate: **{s_wins / len(df_s) * 100:.1f}%** ({s_wins} Wins)")
                st.write(f"• Net P&L: **₹ {df_s['net_pnl'].sum():+,.2f}**")
                st.write(f"• Total Costs: **₹ {df_s['brokerage'].sum() + df_s['taxes'].sum():,.2f}**")
            else:
                st.write("No SENSEX trades recorded yet.")
    else:
        st.write("Analytics will appear once closed trades are recorded.")
