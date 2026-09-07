"""
Daily Algorithmic Trade Summary & Notification Generator
Generates formatted daily reports for Console, WhatsApp, Discord, or Telegram.
"""

import os
import requests
from typing import Dict, List, Optional
from tabulate import tabulate

class TradeNotifier:
    @staticmethod
    def generate_daily_recap(summary: Dict) -> str:
        """Create a clean, formatted daily recap card."""
        date_str = summary.get("date", "")
        tot_trades = summary.get("total_trades", 0)
        wins = summary.get("winning_trades", 0)
        losses = summary.get("losing_trades", 0)
        gross = summary.get("gross_pnl", 0.0)
        charges = summary.get("total_charges", 0.0)
        net = summary.get("net_pnl", 0.0)
        closing_bal = summary.get("closing_cash_balance", 1000000.0)
        trades = summary.get("trades", [])

        status_emoji = "🟢 PROFIT" if net >= 0 else "🔴 LOSS"
        win_rate = (wins / tot_trades * 100.0) if tot_trades > 0 else 0.0

        card = []
        card.append("================================================================")
        card.append(f"  📊 DAILY ALGO TRADE RECAP | {date_str} | {status_emoji}")
        card.append("================================================================")
        card.append(f"• Initial Capital:        ₹ 10,00,000.00")
        card.append(f"• Current Portfolio Cash: ₹ {closing_bal:,.2f}")
        card.append(f"• Today's Gross P&L:      ₹ {gross:+,.2f}")
        card.append(f"• Brokerage & Taxes:      ₹ {charges:,.2f}")
        card.append(f"• Today's Net P&L:        ₹ {net:+,.2f} ({(net/1000000.0)*100:+.2f}%)")
        card.append(f"• Trades Executed:        {tot_trades} (Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%)")
        card.append("----------------------------------------------------------------")
        card.append("  INDIVIDUAL TRADE JOURNAL")
        card.append("----------------------------------------------------------------")

        if not trades:
            card.append("  No trades executed today (Market conditions quarantined or filtered).")
        else:
            table_rows = []
            for t in trades:
                status = "GAIN" if t.get("net_pnl", 0) >= 0 else "LOSS"
                table_rows.append([
                    t.get("strategy"),
                    t.get("instrument"),
                    f"{t.get('quantity')} units",
                    t.get("entry_time", "").split(" ")[-1][:5],
                    f"₹{t.get('entry_price', 0):.1f}",
                    t.get("exit_time", "").split(" ")[-1][:5] if t.get("exit_time") else "Open",
                    f"₹{t.get('exit_price', 0):.1f}" if t.get("exit_price") else "-",
                    t.get("exit_reason", ""),
                    f"₹{t.get('net_pnl', 0):+,.1f}",
                    status
                ])
            
            headers = ["Strategy", "Instrument", "Qty", "Entry", "Buy Px", "Exit", "Sell Px", "Exit Reason", "Net P&L", "Result"]
            card.append(tabulate(table_rows, headers=headers, tablefmt="simple"))

        card.append("================================================================")
        card.append("• Next Active Session: Tomorrow at 09:15 AM IST")
        card.append("• Overnight Risk: 100% Cash | Flat Overnight Exposure")
        card.append("================================================================\n")

        return "\n".join(card)

    @staticmethod
    def send_discord_webhook(text: str, webhook_url: Optional[str] = None) -> bool:
        """Send trade summary alert to a Discord channel via webhook."""
        url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        if not url:
            return False

        try:
            # Discord messages max 2000 chars; truncate if necessary
            payload = {"content": f"```\n{text[:1900]}\n```"}
            res = requests.post(url, json=payload, timeout=5)
            return res.status_code in (200, 204)
        except Exception as e:
            print(f"[Notifier] Failed to send Discord webhook: {e}")
            return False

    @staticmethod
    def send_telegram_alert(text: str, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
        """Send trade summary alert to a Telegram chat."""
        token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat:
            return False

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat,
                "text": f"<pre>{text[:4000]}</pre>",
                "parse_mode": "HTML"
            }
            res = requests.post(url, json=payload, timeout=5)
            return res.status_code == 200
        except Exception as e:
            print(f"[Notifier] Failed to send Telegram alert: {e}")
            return False

    @classmethod
    def dispatch(cls, summary: Dict) -> str:
        """Generate recap card and dispatch to all configured notification channels."""
        recap = cls.generate_daily_recap(summary)
        # Attempt external webhooks if configured
        cls.send_discord_webhook(recap)
        cls.send_telegram_alert(recap)
        return recap
