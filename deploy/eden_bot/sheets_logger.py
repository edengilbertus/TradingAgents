"""
sheets_logger.py — Logs signals and hourly updates to Google Sheets.

Sheet structure (auto-created):
  Tab 1: "Signals"   — one row per signal fired
  Tab 2: "Hourly"    — one row per hourly update
  Tab 3: "Accounts"  — live account metric snapshots
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("eden.sheets")

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.warning("gspread not installed — Google Sheets logging disabled")

from config import GOOGLE_SHEETS_CREDENTIALS_FILE, GOOGLE_SHEET_ID

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client   = None
_spreadsheet = None


def _get_sheet(tab_name: str):
    global _client, _spreadsheet
    if not GSPREAD_AVAILABLE:
        return None
    try:
        if _client is None:
            creds = Credentials.from_service_account_file(
                GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=SCOPES)
            _client = gspread.authorize(creds)
        if _spreadsheet is None:
            _spreadsheet = _client.open_by_key(GOOGLE_SHEET_ID)
        try:
            return _spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            ws = _spreadsheet.add_worksheet(title=tab_name, rows=5000, cols=30)
            _write_headers(ws, tab_name)
            return ws
    except Exception as e:
        logger.error("Google Sheets connection failed: %s", e)
        return None


def _write_headers(ws, tab_name: str) -> None:
    headers = {
        "Signals": [
            "Timestamp", "Symbol", "Direction", "Session",
            "Entry", "Stop", "Target", "Risk_Pts", "RR", "Score",
            "HTF", "PD_Zone", "SMT_Div",
            "Account_1_Units", "Account_1_Risk_USD",
            "Account_2_Units", "Account_2_Risk_USD",
            "Confluence_Details"
        ],
        "Hourly": [
            "Timestamp", "Signals_Today",
            "A1_Equity", "A1_Profit", "A1_MaxLoss_Remaining", "A1_Daily_Remaining",
            "A2_Equity", "A2_Profit", "A2_MaxLoss_Remaining", "A2_Daily_Remaining",
        ],
        "Accounts": [
            "Timestamp", "Account_ID", "Name", "Equity", "Balance",
            "Profit_Achieved", "Profit_Target", "Max_Loss_Remaining",
            "Daily_Remaining", "Status"
        ],
    }
    if tab_name in headers:
        ws.append_row(headers[tab_name], value_input_option="RAW")


def log_signal(signal: dict, plans: list[dict]) -> None:
    ws = _get_sheet("Signals")
    if ws is None:
        return
    now = signal["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    a1 = next((p for p in plans if list(plans).index(p) == 0), {})
    a2 = next((p for p in plans if list(plans).index(p) == 1), {})
    row = [
        now,
        signal["symbol"],
        signal["direction"].upper(),
        signal["session"],
        signal["entry"],
        signal["stop"],
        signal["target"],
        signal["risk_pts"],
        signal["rr"],
        signal["score"],
        signal["htf"],
        signal["pd_zone"],
        str(signal["smt_div"]),
        a1.get("units", "BLOCKED"),
        a1.get("risk_usd", "BLOCKED"),
        a2.get("units", "BLOCKED"),
        a2.get("risk_usd", "BLOCKED"),
        " | ".join(signal.get("details", [])),
    ]
    try:
        ws.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Signal logged to Google Sheets")
    except Exception as e:
        logger.error("Failed to log signal to Sheets: %s", e)


def log_hourly(summaries: list[dict], signals_today: int) -> None:
    ws = _get_sheet("Hourly")
    if ws is None:
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    s1  = summaries[0] if len(summaries) > 0 else {}
    s2  = summaries[1] if len(summaries) > 1 else {}
    row = [
        now, signals_today,
        s1.get("equity", ""),       s1.get("profit_achieved", ""),
        s1.get("max_loss_remaining", ""), s1.get("daily_remaining", ""),
        s2.get("equity", ""),       s2.get("profit_achieved", ""),
        s2.get("max_loss_remaining", ""), s2.get("daily_remaining", ""),
    ]
    try:
        ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        logger.error("Failed to log hourly update to Sheets: %s", e)


def log_account_snapshot(summaries: list[dict]) -> None:
    ws = _get_sheet("Accounts")
    if ws is None:
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for s in summaries:
        row = [
            now, s["account_id"], s["name"], s["equity"], s["balance"],
            s["profit_achieved"], s["profit_target"],
            s["max_loss_remaining"], s["daily_remaining"], s["status"]
        ]
        try:
            ws.append_row(row, value_input_option="USER_ENTERED")
        except Exception as e:
            logger.error("Failed to log account snapshot: %s", e)
