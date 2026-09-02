import os
import uuid
import re
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("AGENT_LEASH_BACKEND_URL", os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))

st.set_page_config(page_title="Agent Leash", page_icon="🛡️", layout="wide")


CSS = """
<style>
    :root {
        --bg: #040b14;
        --bg-2: #091b2d;
        --panel: rgba(13, 24, 38, 0.9);
        --panel-strong: rgba(17, 31, 49, 0.96);
        --panel-soft: rgba(15, 27, 41, 0.8);
        --line: rgba(121, 162, 255, 0.2);
        --text: #edf5ff;
        --muted: #a8bfd8;
        --accent: #5da7ff;
        --accent-strong: #2b7ef7;
        --cyan: #67e8f9;
        --green: #33d39a;
        --amber: #f5b451;
        --red: #ff6b6b;
        --purple: #9f7aea;
        --shadow: 0 18px 40px rgba(0,0,0,0.28);
    }
    html, body, [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(93, 167, 255, 0.15), transparent 22%),
            radial-gradient(circle at bottom right, rgba(103, 232, 249, 0.12), transparent 24%),
            linear-gradient(180deg, var(--bg) 0%, #071722 100%);
        color: var(--text);
        font-family: "Segoe UI", Inter, sans-serif;
    }
    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 1.4rem;
    }
    .agent-shell {
        display: flex;
        min-height: 100vh;
        gap: 1.25rem;
        align-items: flex-start;
    }
    .agent-sidebar {
        width: 250px;
        background: rgba(8, 18, 31, 0.94);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 1rem 0.9rem;
        box-shadow: var(--shadow);
        position: sticky;
        top: 1rem;
    }
    .brand-mark {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.5rem 0.45rem 1rem;
        border-bottom: 1px solid var(--line);
        margin-bottom: 1rem;
    }
    .brand-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.2rem;
        height: 2.2rem;
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(93,167,255,0.18), rgba(103,232,249,0.18));
        border: 1px solid rgba(103,232,249,0.35);
        color: var(--cyan);
        font-size: 1.1rem;
        font-weight: 800;
    }
    .brand-title {
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        color: var(--text);
    }
    .danger-tag {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(255,255,255,0.04);
        color: var(--muted);
    }
    .nav-stack {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-top: 0.8rem;
    }
    .nav-item {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.7rem 0.8rem;
        border-radius: 12px;
        color: var(--muted);
        font-size: 0.92rem;
        border: 1px solid transparent;
        background: transparent;
    }
    .nav-item.active {
        background: rgba(93, 167, 255, 0.08);
        border-color: rgba(93, 167, 255, 0.2);
        color: var(--text);
    }
    .nav-dot {
        width: 0.45rem;
        height: 0.45rem;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 0 4px rgba(93, 167, 255, 0.12);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] {
        padding: 0.1rem 0;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        color: var(--muted) !important;
        background: transparent;
        border: 1px solid transparent;
        border-radius: 12px;
        padding: 0.68rem 0.75rem;
        margin: 0.12rem 0;
        font-size: 0.92rem;
        transition: background 0.15s ease, border-color 0.15s ease;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(93, 167, 255, 0.08);
        border-color: rgba(93, 167, 255, 0.2);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        color: var(--text) !important;
        background: rgba(93, 167, 255, 0.08);
        border-color: rgba(93, 167, 255, 0.2);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
        margin: 0;
    }
    .sidebar-card {
        margin-top: 1.2rem;
        background: rgba(13, 24, 38, 0.9);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 0.9rem;
    }
    .sidebar-card h4 {
        margin: 0 0 0.7rem 0;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        color: var(--muted);
        text-transform: uppercase;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(51, 211, 154, 0.12);
        border: 1px solid rgba(51, 211, 154, 0.25);
        border-radius: 999px;
        padding: 0.38rem 0.7rem;
        margin-bottom: 0.6rem;
        color: #d7f9ec;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .status-pill .dot {
        width: 0.45rem;
        height: 0.45rem;
        border-radius: 50%;
        background: var(--green);
        box-shadow: 0 0 0 5px rgba(51, 211, 154, 0.12);
    }
    .risk-overview {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        color: var(--muted);
    }
    .risk-number {
        font-size: 1.4rem;
        font-weight: 800;
        color: var(--text);
    }
    .main-panel {
        flex: 1;
        min-width: 0;
    }
    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        background: rgba(10, 20, 32, 0.8);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 0.9rem 1.1rem;
        box-shadow: var(--shadow);
        margin-bottom: 0.9rem;
    }
    .brand-wrap {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }
    .brand-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.8rem;
        height: 2.8rem;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(93,167,255,0.18), rgba(103,232,249,0.18));
        border: 1px solid rgba(103,232,249,0.35);
        color: var(--cyan);
        font-size: 1.2rem;
        box-shadow: 0 10px 24px rgba(93,167,255,0.12);
    }
    .brand-copy {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }
    .brand-small {
        display: block;
        font-size: 0.72rem;
        color: #edf6ff;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        font-weight: 800;
        line-height: 1.2;
        margin-bottom: 0.22rem;
        white-space: nowrap;
    }
    .brand {
        font-size: clamp(1.4rem, 2vw, 2.15rem);
        font-weight: 800;
        letter-spacing: 0.02em;
        line-height: 1.2;
        color: var(--text);
    }
    .top-subtitle {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 0.12rem;
        line-height: 1.4;
    }
    .top-status {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 0.2rem;
    }
    .status {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        background: rgba(51, 211, 154, 0.08);
        border: 1px solid rgba(51, 211, 154, 0.25);
        border-radius: 999px;
        padding: 0.45rem 0.8rem;
        color: #d7f9ec;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .dot {
        width: 0.55rem;
        height: 0.55rem;
        border-radius: 50%;
        background: var(--green);
        box-shadow: 0 0 0 5px rgba(51, 211, 154, 0.12);
    }
    .status-note {
        color: var(--muted);
        font-size: 0.74rem;
    }
    .card {
        background: rgba(15, 27, 41, 0.92);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 0.9rem 0.95rem;
        box-shadow: var(--shadow);
        height: 100%;
    }
    .card h3 {
        margin: 0 0 0.7rem 0;
        font-size: 1.02rem;
        letter-spacing: 0.02em;
        color: var(--text);
    }
    .card-subtitle {
        color: var(--muted);
        font-size: 0.78rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.9rem;
    }
    .meta-label {
        color: var(--muted);
        font-size: 0.73rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.25rem;
    }
    .meta-value {
        margin-bottom: 0.8rem;
        font-size: 0.97rem;
        line-height: 1.6;
        color: var(--text);
    }
    .pill {
        display: inline-block;
        padding: 0.28rem 0.6rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-right: 0.45rem;
        margin-bottom: 0.45rem;
    }
    .pill-allow { background: rgba(51, 211, 154, 0.14); color: #dffef5; border: 1px solid rgba(51, 211, 154, 0.3); }
    .pill-ask { background: rgba(245, 180, 81, 0.14); color: #ffe9b8; border: 1px solid rgba(245, 180, 81, 0.3); }
    .pill-block { background: rgba(255, 107, 107, 0.14); color: #ffd1d1; border: 1px solid rgba(255, 107, 107, 0.3); }
    .decision-box {
        border-radius: 18px;
        padding: 1rem 1.1rem;
        border: 1px solid var(--line);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        min-height: 160px;
        margin-bottom: 0.8rem;
    }
    .decision-box.allow { background: rgba(51, 211, 154, 0.08); border-color: rgba(51, 211, 154, 0.35); }
    .decision-box.ask { background: rgba(245, 180, 81, 0.08); border-color: rgba(245, 180, 81, 0.3); }
    .decision-box.block { background: rgba(255, 107, 107, 0.08); border-color: rgba(255, 107, 107, 0.3); }
    .decision-text {
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        margin-top: 0.3rem;
    }
    .decision-box.allow .decision-text { color: var(--green); }
    .decision-box.ask .decision-text { color: var(--amber); }
    .decision-box.block .decision-text { color: var(--red); }
    .risk-bar {
        width: 100%;
        height: 0.5rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.06);
        overflow: hidden;
        margin: 0.45rem 0 0.7rem;
        border: 1px solid rgba(255,255,255,0.04);
    }
    .risk-bar > span {
        display: block;
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, var(--green), var(--amber), var(--red));
    }
    .scenario-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 1rem;
        margin-top: 1.2rem;
    }
    .scenario-card {
        border-radius: 16px;
        border: 1px solid var(--line);
        background: linear-gradient(180deg, rgba(17,33,48,0.96), rgba(12,20,31,0.96));
        padding: 1rem;
        height: 100%;
        box-shadow: var(--shadow);
    }
    .scenario-icon {
        font-size: 1.4rem;
        margin-bottom: 0.5rem;
    }
    .scenario-name {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.45rem;
        color: var(--text);
    }
    .scenario-desc {
        color: var(--muted);
        font-size: 0.84rem;
        min-height: 76px;
        line-height: 1.5;
        margin-bottom: 0.9rem;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 700;
        padding: 0.62rem 0.9rem;
        box-shadow: 0 8px 20px rgba(43, 126, 247, 0.25);
    }
    .stButton > button:hover { filter: brightness(1.08); }
    .approval-box, .payment-box {
        background: rgba(76, 141, 255, 0.08);
        border: 1px solid rgba(76, 141, 255, 0.25);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        margin-top: 1.2rem;
    }
    .success-box {
        background: rgba(51, 211, 154, 0.08);
        border: 1px solid rgba(51, 211, 154, 0.25);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        margin-top: 1.2rem;
    }
    .error-box {
        background: rgba(255, 107, 107, 0.08);
        color: #ffd3d3;
        border: 1px solid rgba(255, 107, 107, 0.25);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        margin-top: 1rem;
    }
    .footer-note {
        margin-top: 1.8rem;
        padding-top: 1.1rem;
        border-top: 1px solid var(--line);
        color: var(--muted);
        font-size: 0.8rem;
        line-height: 1.7;
        text-align: center;
    }
    .muted { color: var(--muted); }
    .section-spacer { margin-top: 0.7rem; }
    @media (max-width: 1200px) {
        .scenario-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    @media (max-width: 900px) {
        .agent-shell {
            display: block;
        }
        .agent-sidebar {
            width: 100%;
            position: static;
            margin-bottom: 1rem;
        }
        .scenario-grid {
            grid-template-columns: 1fr;
        }
        .topbar {
            flex-direction: column;
            align-items: flex-start;
        }
        .top-status {
            align-items: flex-start;
        }
    }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


def fetch_json(url: str):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def post_json(url: str, payload=None):
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def new_request_id() -> str:
    return str(uuid.uuid4())


def stable_request_id(state_key: str, logical_input=None) -> str:
    input_key = f"{state_key}_input"
    if st.session_state.get(input_key) != logical_input:
        st.session_state[input_key] = logical_input
        st.session_state[state_key] = new_request_id()
    return st.session_state[state_key]


def render_value(label: str, value):
    st.markdown(f"<div class='meta-label'>{label}</div>", unsafe_allow_html=True)
    if value is None:
        st.markdown("<div class='meta-value muted'>Not specified</div>", unsafe_allow_html=True)
    elif isinstance(value, list):
        if value:
            st.markdown(
                "<div class='meta-value'>" + "<br>".join(f"• {item}" for item in value) + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<div class='meta-value muted'>None</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='meta-value'>{value}</div>", unsafe_allow_html=True)


def render_policy_badge(decision: str):
    decision = str(decision).upper()
    if decision == "ALLOW":
        return "pill pill-allow"
    if decision == "ASK":
        return "pill pill-ask"
    return "pill pill-block"


def unique_reasons(reasons):
    return list(dict.fromkeys(str(reason) for reason in reasons if reason))


def format_policy_reason(reason):
    """Make internal paise values user-friendly without changing policy logic."""
    text = str(reason)

    def replace_paise(match):
        paise = int(match.group(1))
        if paise % 100 == 0:
            return f"₹{paise / 100:.0f}"
        return f"₹{paise / 100:.2f}"

    return re.sub(r"(?<![\\d.])(\\d+)\\s+paise\\b", replace_paise, text)


def risk_label_for_result(result):
    if not isinstance(result, dict):
        return "AWAITING DECISION"
    decision = result.get("policy_decision", result)
    decision_name = str(decision.get("decision", "")).upper() if isinstance(decision, dict) else ""
    if decision_name == "ALLOW":
        return "LOW RISK"
    if decision_name == "BLOCK":
        return "HIGH RISK"
    if decision_name == "ASK":
        return "REVIEW REQUIRED"
    return "AWAITING DECISION"


def latest_evaluation_result():
    for state_key in ("latest_evaluation_result", "ai_buyer_result", "ask_demo_result", "result"):
        result = st.session_state.get(state_key)
        if isinstance(result, dict) and "error" not in result:
            return result
    return None


def render_status_band():
    current_result = latest_evaluation_result()
    risk_label = risk_label_for_result(current_result)

    st.sidebar.markdown(
        """
        <div class="agent-sidebar">
            <div class="brand-mark">
                <div class="brand-icon">🛡️</div>
                <div class="brand-title">AGENT LEASH</div>
            </div>
            <div class="nav-stack">
                <div class="nav-item active"><span class="nav-dot"></span>Dashboard</div>
            </div>
            <div class="sidebar-card">
                <h4>System Status</h4>
                <div class="status-pill"><span class="dot"></span>ACTIVE</div>
            </div>
            <div class="sidebar-card">
                <h4>Policy Enforcement</h4>
                <div class="status-pill"><span class="dot"></span>ON</div>
            </div>
            <div class="sidebar-card">
                <h4>Current Risk</h4>
                <div class="risk-overview"><span>Risk</span><span class="risk-number">{risk_label}</span></div>
            </div>
        </div>
        """.format(risk_label=risk_label),
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="background: rgba(10, 20, 32, 0.82); border: 1px solid rgba(121, 162, 255, 0.2); border-radius: 18px; padding: 2.1rem 1.15rem 1.4rem 1.15rem; margin: 0.55rem 0 0.8rem 0; box-shadow: 0 12px 28px rgba(0, 0, 0, 0.18);">
            <div style="display:flex; align-items:center; gap:0.5rem; color:#edf6ff; font-size:1.2rem; letter-spacing:0.12em; text-transform:uppercase; font-weight:800; margin:0 0 0.45rem 0; line-height:1.3;">
                <span style="font-size:1.2rem; line-height:1;">🛡️</span>
                <span>AGENT LEASH</span>
            </div>
            <div style="font-size:2.15rem; line-height:1.2; font-weight:800; color:#edf6ff; margin:0 0 0.2rem 0; letter-spacing:0.02em;">AI Transaction Security Layer</div>
            <div style="font-size:1rem; color:#a8bfd8; line-height:1.45; margin:0;">Security layer for AI-powered transactions</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def scenario_cards():
    try:
        scenarios = fetch_json(f"{BASE_URL}/demo/scenarios")
    except requests.RequestException:
        return []

    return scenarios


def audit_records():
    try:
        return fetch_json(f"{BASE_URL}/audit")
    except requests.RequestException:
        return None


def compact_audit_records(records):
    compacted = []
    seen_transaction_ids = set()
    for record in records:
        transaction_id = record.get("transaction_id")
        if transaction_id and transaction_id in seen_transaction_ids:
            continue
        if transaction_id:
            seen_transaction_ids.add(transaction_id)
        compacted.append(record)
    return compacted


def render_audit_record(record):
    decision = str(record.get("decision", "")).upper()
    approval = record.get("human_decision") or "Not reviewed"
    payment = record.get("payment_status") or "No order created"
    st.markdown(
        "<div class='card' style='margin-bottom: 0.7rem;'>"
        f"<div class='meta-label'>Timestamp</div><div class='meta-value'>{record.get('timestamp') or 'Not available'}</div>"
        f"<div class='meta-label'>Transaction</div><div class='meta-value'>{record.get('transaction_id') or 'Not available'}</div>"
        f"<div class='meta-label'>Decision / Risk</div><div class='meta-value'><strong>{decision or 'Not available'}</strong> / {record.get('risk_score')}</div>"
        f"<div class='meta-label'>Policy reason</div><div class='meta-value'>{record.get('policy_reason') or 'None'}</div>"
        f"<div class='meta-label'>Human review</div><div class='meta-value'>{approval}"
        f"{f' by {record.get("reviewer")}' if record.get('reviewer') else ''}</div>"
        f"<div class='meta-label'>Payment / order status</div><div class='meta-value'>{payment}"
        f"{f' ({record.get("razorpay_order_id")})' if record.get('razorpay_order_id') else ''}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_audit_trail(records):
    st.markdown("<div class='card-subtitle' style='margin-top: 1.2rem;'>AUDIT TRAIL</div>", unsafe_allow_html=True)
    if records is None:
        render_error("Unable to load the audit trail from the backend.")
        return
    if not records:
        st.markdown("<div class='meta-value muted'>No audit records yet.</div>", unsafe_allow_html=True)
        return

    compacted_records = compact_audit_records(records)
    visible_records = compacted_records[:4]
    for record in visible_records:
        render_audit_record(record)

    if len(compacted_records) > len(visible_records) or len(records) > len(visible_records):
        with st.expander(f"View full history ({len(records)} records)"):
            for record in records:
                render_audit_record(record)


def render_user_intent(intent):
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3>👤 User Authorization</h3>", unsafe_allow_html=True)
        if intent:
            cols = st.columns(2)
            fields = [
                ("User instruction", intent.get("instruction")),
                ("Maximum authorized amount", intent.get("max_amount")),
                ("Allowed categories", intent.get("allowed_categories")),
                ("Allowed colors", intent.get("allowed_colors")),
                ("Allowed sizes", intent.get("allowed_sizes")),
                ("Subscription permission", intent.get("allow_subscription")),
                ("Add-on permission", intent.get("allow_addons")),
                ("Daily limit", intent.get("daily_limit")),
                ("Session limit", intent.get("session_limit")),
            ]
            for index, (label, value) in enumerate(fields):
                with cols[index % 2]:
                    render_value(label, value)
        st.markdown("</div>", unsafe_allow_html=True)


def render_proposed_transaction(tx):
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3>🤖 AI Proposed Transaction</h3>", unsafe_allow_html=True)
        if tx:
            render_value("Merchant", tx.get("merchant_id"))
            total = tx.get("total_amount")
            if total is not None:
                st.markdown("<div class='meta-label'>Total amount</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='meta-value'>{total}</div>", unsafe_allow_html=True)

            items = tx.get("items", [])
            if items:
                for index, item in enumerate(items, 1):
                    st.markdown(f"<div class='meta-label'>Item {index}</div>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div class='meta-value'><strong>{item.get('product_name')}</strong><br>"
                        f"Qty: {item.get('quantity')} | Unit price: {item.get('unit_price')} | Category: {item.get('category')}<br>"
                        f"Color: {item.get('color')} | Size: {item.get('size')}<br>"
                        f"Subscription: {item.get('is_subscription')} | Add-on: {item.get('is_addon')}</div>",
                        unsafe_allow_html=True,
                    )
        st.markdown("</div>", unsafe_allow_html=True)


def render_policy_decision(decision):
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3>🛡️ AGENT LEASH DECISION</h3>", unsafe_allow_html=True)
        if decision:
            badge = str(decision.get("decision", "")).upper()
            st.markdown(
                f"<div class='decision-box {badge.lower() if badge in ('ALLOW', 'ASK', 'BLOCK') else 'allow'}'>"
                f"<div class='meta-label'>Decision</div><div class='decision-text'>{badge}</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"<div class='meta-label'>Risk Score</div><div class='meta-value'>{decision.get('risk_score')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta-label'>Human Confirmation</div><div class='meta-value'>{decision.get('requires_human_confirmation')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta-label'>Violated Rules</div>", unsafe_allow_html=True)
            if decision.get("violated_rules"):
                st.markdown("<div class='meta-value'>" + "<br>".join(f"• {rule}" for rule in decision.get("violated_rules", [])) + "</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='meta-value muted'>None</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta-label'>Policy Reasons</div>", unsafe_allow_html=True)
            reasons = unique_reasons(decision.get("reasons", []))
            if reasons:
                display_reasons = [format_policy_reason(reason) for reason in reasons]
                st.markdown("<div class='meta-value'>" + "<br>".join(f"• {reason}" for reason in display_reasons) + "</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='meta-value muted'>No policy reasons provided.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_human_review(tx, decision):
    if not tx or not decision:
        return
    if str(decision.get("decision", "")).upper() != "ASK":
        return
    if not decision.get("requires_human_confirmation"):
        return

    decision_transaction_id = str(decision.get("transaction_id") or tx.get("transaction_id") or "").strip()
    if not decision_transaction_id:
        render_error("No valid transaction ID is available for human review. Please re-run the scenario.")
        return

    st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background: rgba(76, 141, 255, 0.10); border: 1px solid rgba(76, 141, 255, 0.35); border-radius: 16px; padding: 1rem 1.1rem; color: #eaf3ff;">
            <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #b7d0ff; margin-bottom: 0.35rem;">Human Review Required</div>
            <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;">Transaction requires manual review</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("approval_form"):
        row = st.columns(2)
        with row[0]:
            st.text_input("Reviewer name", key="reviewer_name")
        with row[1]:
            st.text_input("Transaction ID", value=decision_transaction_id, disabled=True)

        st.text_area("Optional note", key="approval_note", placeholder="Add reviewer note")

        st.write(f"Total amount: {tx.get('total_amount')}")
        st.write(f"Risk score: {decision.get('risk_score')}")

        col_approve, col_reject = st.columns(2)
        with col_approve:
            approve_clicked = st.form_submit_button("APPROVE TRANSACTION", use_container_width=True)
        with col_reject:
            reject_clicked = st.form_submit_button("REJECT TRANSACTION", use_container_width=True)

        if approve_clicked or reject_clicked:
            reviewer = st.session_state.get("reviewer_name", "").strip()
            if not reviewer:
                render_error("Reviewer name is required.")
            else:
                payload = {
                    "transaction_id": decision_transaction_id,
                    "original_decision": "ASK",
                    "human_decision": "APPROVE" if approve_clicked else "REJECT",
                    "reviewer": reviewer,
                    "note": st.session_state.get("approval_note", "").strip() or None,
                }
                try:
                    response = post_json(f"{BASE_URL}/approval", payload)
                    if response.get("human_decision") == "APPROVE":
                        st.session_state.approval_state = "APPROVED"
                        st.success("Approval recorded")
                    else:
                        st.session_state.approval_state = "REJECTED"
                        st.error("Transaction rejected")
                except requests.RequestException as exc:
                    render_error(f"Approval request failed: {exc}")


def render_error(message: str):
    st.markdown(f"<div class='error-box'>{message}</div>", unsafe_allow_html=True)


def render_ai_buyer_section():
    st.markdown("<div class='card-subtitle' style='margin-top: 1.2rem;'>🤖 AI BUYER</div>", unsafe_allow_html=True)
    instruction = st.text_area(
        "User instruction",
        value="Buy black running shoes, size 9, under ₹3000. No extras.",
        key="ai_buyer_instruction",
        height=90,
    )

    if st.button("Analyze & Propose Purchase", key="analyze_ai_buyer", use_container_width=True):
        if not instruction.strip():
            st.session_state.ai_buyer_result = {"error": "Instruction cannot be empty."}
        else:
            st.session_state.approval_state = None
            st.session_state.payment_order = None
            try:
                payload = post_json(
                    f"{BASE_URL}/agent/buy",
                    {
                        "instruction": instruction,
                        "request_id": stable_request_id("ai_buyer_request_id", instruction),
                    },
                )
                st.session_state.ai_buyer_result = payload
                st.session_state.latest_evaluation_result = payload
                st.rerun()
            except requests.RequestException as exc:
                detail = getattr(getattr(exc, "response", None), "json", lambda: {})()
                message = detail.get("detail") if isinstance(detail, dict) else None
                st.session_state.ai_buyer_result = {"error": message or "AI service temporarily unavailable. Please try again later."}

    result = st.session_state.get("ai_buyer_result")
    if not result:
        return
    if "error" in result:
        render_error(result["error"])
        return

    intent = result.get("user_intent", {})
    tx = result.get("ai_buyer_proposal", {})
    decision_name = str(result.get("decision", "")).upper()
    decision = {
        "decision": decision_name,
        "risk_score": result.get("risk_score"),
        "violated_rules": result.get("violated_rules", []),
        "reasons": result.get("policy_reasons", []),
        "transaction_id": result.get("transaction_id"),
        "requires_human_confirmation": decision_name == "ASK",
    }

    col_user, col_tx, col_decision = st.columns([1.15, 1.15, 1])
    with col_user:
        render_user_intent(intent)
    with col_tx:
        render_proposed_transaction(tx)
    with col_decision:
        render_policy_decision(decision)

    if decision_name == "ALLOW":
        st.success("ALLOW: eligible for the existing Razorpay TEST payment flow.")
    elif decision_name == "BLOCK":
        st.error("BLOCK: payment cannot proceed.")
    render_human_review(tx, decision)
    render_payment_flow(tx, decision, "ai_buyer")


def render_payment_flow(tx, decision, ui_instance):
    if not tx or not decision:
        return

    if "error" in decision:
        return

    decision_name = str(decision.get("decision", "")).upper()
    transaction_id = str(decision.get("transaction_id") or tx.get("transaction_id") or "").strip()

    if not transaction_id:
        render_error("No valid transaction ID is available. Razorpay order creation cannot proceed.")
        return

    if decision_name == "BLOCK":
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background: rgba(239, 90, 90, 0.10); border: 1px solid rgba(239, 90, 90, 0.25); border-radius: 16px; padding: 1rem 1.1rem; color: #eaf3ff;">
                <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #ffc3c3; margin-bottom: 0.35rem;">Transaction Blocked</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;">No payment order can be created.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if decision_name == "ASK":
        if st.session_state.get("approval_state") == "APPROVED":
            st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="background: rgba(32, 201, 151, 0.10); border: 1px solid rgba(32, 201, 151, 0.25); border-radius: 16px; padding: 1rem 1.1rem; color: #eaf3ff;">
                    <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #bff9df; margin-bottom: 0.35rem;">Approved — Payment Ready</div>
                    <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;">Create Razorpay TEST Order</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif st.session_state.get("approval_state") == "REJECTED":
            st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="background: rgba(239, 90, 90, 0.10); border: 1px solid rgba(239, 90, 90, 0.25); border-radius: 16px; padding: 1rem 1.1rem; color: #eaf3ff;">
                    <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #ffc3c3; margin-bottom: 0.35rem;">Transaction Rejected</div>
                    <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;">A payment order will not be created.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return
        else:
            st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="background: rgba(244, 185, 66, 0.10); border: 1px solid rgba(244, 185, 66, 0.25); border-radius: 16px; padding: 1rem 1.1rem; color: #eaf3ff;">
                    <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #ffe7ad; margin-bottom: 0.35rem;">Human Confirmation Required</div>
                    <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;">Approval is required before a payment order can be created.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

    if decision_name == "ALLOW":
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background: rgba(32, 201, 151, 0.10); border: 1px solid rgba(32, 201, 151, 0.25); border-radius: 16px; padding: 1rem 1.1rem; color: #eaf3ff;">
                <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #bff9df; margin-bottom: 0.35rem;">Payment Ready</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;">Create Razorpay TEST Order</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("Create Test Payment", key=f"payment_{ui_instance}_{transaction_id}"):
        try:
            response = post_json(f"{BASE_URL}/transactions/{transaction_id}/order")
            st.session_state.payment_order = response
        except requests.RequestException as exc:
            render_error(f"Order creation failed: {exc}")
            st.session_state.payment_order = {"error": str(exc)}

    if st.session_state.get("payment_order"):
        order = st.session_state["payment_order"]
        if "error" not in order:
            st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="background: rgba(76, 141, 255, 0.10); border: 1px solid rgba(76, 141, 255, 0.35); border-radius: 16px; padding: 1rem 1.1rem; color: #eaf3ff;">
                    <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #b7d0ff; margin-bottom: 0.35rem;">Razorpay TEST Order Created</div>
                    <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;">Order is ready for test-mode payment steps.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write(f"Order ID: {order.get('razorpay_order_id')}")
            st.write(f"Amount: {order.get('amount')}")
            st.write(f"Currency: {order.get('currency')}")
            st.write(f"Status: {order.get('status')}")



def render_page_header(title=None, subtitle=None):
    title = title or "AI Transaction Security Layer"
    subtitle = subtitle or "Security layer for AI-powered transactions"
    st.markdown(
        f"""
        <div style="background: rgba(10, 20, 32, 0.82); border: 1px solid rgba(121, 162, 255, 0.2); border-radius: 18px; padding: 1.6rem 1.15rem 1.25rem 1.15rem; margin: 0.55rem 0 1rem 0; box-shadow: 0 12px 28px rgba(0,0,0,0.18);">
            <div style="display:flex; align-items:center; gap:0.5rem; color:#edf6ff; font-size:1.1rem; letter-spacing:0.12em; text-transform:uppercase; font-weight:800; margin-bottom:0.35rem;">
                <span>🛡️</span><span>AGENT LEASH</span>
            </div>
            <div style="font-size:2rem; line-height:1.2; font-weight:800; color:#edf6ff;">{title}</div>
            <div style="font-size:0.95rem; color:#a8bfd8; line-height:1.45; margin-top:0.2rem;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_navigation():
    current_result = latest_evaluation_result()
    risk_label = risk_label_for_result(current_result)

    st.sidebar.markdown(
        """
        <div class="brand-mark" style="margin-bottom:0.7rem;">
            <div class="brand-icon">🛡️</div>
            <div class="brand-title">AGENT LEASH</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard Status", "Policy Enforcement", "Current Risk", "Audit Trail", "Demo / Testing"],
        key="agent_leash_page",
        label_visibility="collapsed",
    )

    st.sidebar.markdown(
        f"""
        <div class="sidebar-card">
            <h4>System Status</h4>
            <div class="status-pill"><span class="dot"></span>ACTIVE</div>
        </div>
        <div class="sidebar-card">
            <h4>Current Risk</h4>
            <div class="risk-overview"><span>Risk</span><span class="risk-number">{risk_label}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return page


def render_transaction_result(result, ui_instance="transaction"):
    if not result:
        return
    if "error" in result:
        render_error(result["error"])
        return
    intent = result.get("user_intent", {})
    tx = result.get("proposed_transaction") or result.get("ai_buyer_proposal", {})
    decision = result.get("policy_decision", {})
    if not decision and result.get("decision"):
        decision_name = str(result.get("decision", "")).upper()
        decision = {
            "decision": decision_name,
            "risk_score": result.get("risk_score"),
            "violated_rules": result.get("violated_rules", []),
            "reasons": result.get("policy_reasons", []),
            "transaction_id": result.get("transaction_id"),
            "requires_human_confirmation": decision_name == "ASK",
        }
    columns = st.columns([1.15, 1.15, 1])
    with columns[0]:
        render_user_intent(intent)
    with columns[1]:
        render_proposed_transaction(tx)
    with columns[2]:
        render_policy_decision(decision)
    render_human_review(tx, decision)
    render_payment_flow(tx, decision, ui_instance)


def render_ask_demo():
    st.markdown("<div class='card-subtitle' style='margin-top: 1.2rem;'>ASK DEMONSTRATION</div>", unsafe_allow_html=True)
    if st.button("Run ASK Demo", key="run_ask_demo", use_container_width=True):
        st.session_state.approval_state = None
        st.session_state.payment_order = None
        try:
            payload = post_json(
                f"{BASE_URL}/demo/ask",
                {"request_id": stable_request_id("ask_demo_request_id", "ASK_DEMO")},
            )
            st.session_state.ask_demo_result = payload
            st.session_state.latest_evaluation_result = payload
            st.rerun()
        except requests.RequestException as exc:
            st.session_state.ask_demo_result = {"error": f"ASK demo request failed: {exc}"}

    ask_demo_result = st.session_state.get("ask_demo_result")
    if ask_demo_result:
        if "error" in ask_demo_result:
            render_error(ask_demo_result["error"])
        else:
            ask_intent = ask_demo_result.get("user_intent", {})
            ask_tx = ask_demo_result.get("proposed_transaction", {})
            ask_decision = ask_demo_result.get("policy_decision", {})
            ask_columns = st.columns([1.15, 1.15, 1])
            with ask_columns[0]:
                render_user_intent(ask_intent)
            with ask_columns[1]:
                render_proposed_transaction(ask_tx)
            with ask_columns[2]:
                render_policy_decision(ask_decision)
            render_human_review(ask_tx, ask_decision)
            render_payment_flow(ask_tx, ask_decision, "ask_demo")


def get_scenario_list():
    scenarios = scenario_cards()
    return scenarios if scenarios else [
        {"name": "SAFE_PURCHASE", "description": "A fully authorized purchase that matches the user's budget, category, and size constraints.", "icon": "✅"},
        {"name": "UNAUTHORIZED_ADDON", "description": "The base product is allowed, but the AI adds an unauthorized warranty or accessory add-on.", "icon": "🧩"},
        {"name": "UNAUTHORIZED_SUBSCRIPTION", "description": "The AI adds a subscription or recurring fee that the user did not authorize.", "icon": "💳"},
        {"name": "OVER_LIMIT", "description": "The AI proposes a cart that exceeds the user's maximum authorized spend.", "icon": "⚠️"},
        {"name": "AGGREGATE_SPLIT", "description": "Two or more separate reasonable charges are combined to exceed the user's daily or session limit.", "icon": "🔗"},
    ]


def render_demo_scenarios():
    scenario_list = get_scenario_list()
    if not scenario_list:
        render_error("Unable to load demo scenarios from the backend.")
        return

    st.markdown("<div class='card-subtitle' style='margin-top: 1.2rem;'>DEMO SCENARIOS</div>", unsafe_allow_html=True)
    scenario_icons = {"SAFE_PURCHASE": "✅", "UNAUTHORIZED_ADDON": "🧩", "UNAUTHORIZED_SUBSCRIPTION": "💳", "OVER_LIMIT": "⚠️", "AGGREGATE_SPLIT": "🔗"}
    scenario_cols = st.columns(len(scenario_list))
    for idx, scenario in enumerate(scenario_list):
        with scenario_cols[idx]:
            st.markdown(
                f"""
                <div class='scenario-card'>
                    <div class='scenario-icon'>{scenario.get('icon', scenario_icons.get(scenario['name'], '🧪'))}</div>
                    <div class='scenario-name'>{scenario['name']}</div>
                    <div class='scenario-desc'>{scenario.get('description', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Run Scenario", key=f"run_scenario_{scenario['name']}_{idx}", use_container_width=True):
                try:
                    payload = post_json(
                        f"{BASE_URL}/demo/scenarios/{scenario['name']}",
                        {"request_id": stable_request_id(f"scenario_request_id_{scenario['name']}", scenario["name"])},
                    )
                    st.session_state.result = payload
                    st.session_state.latest_evaluation_result = payload
                    st.rerun()
                except requests.RequestException as exc:
                    st.session_state.result = {"error": f"API request failed: {exc}"}

    result = st.session_state.get("result")
    if result:
        if "error" in result:
            render_error(result["error"])
        else:
            intent = result.get("user_intent", {})
            tx = result.get("proposed_transaction", {})
            decision = result.get("policy_decision", {})
            cols = st.columns([1.15, 1.15, 1])
            with cols[0]:
                render_user_intent(intent)
            with cols[1]:
                render_proposed_transaction(tx)
            with cols[2]:
                render_policy_decision(decision)
            render_human_review(tx, decision)
            render_payment_flow(tx, decision, "scenario")


def render_current_risk_page():
    render_page_header("Current Risk", "Latest security evaluation")
    result = latest_evaluation_result()
    if not result:
        st.markdown("<div class='card'><div class='meta-label'>CURRENT RISK</div><div class='decision-text'>AWAITING DECISION</div><div class='meta-value muted'>Run an AI Buyer evaluation or demo scenario to calculate risk.</div></div>", unsafe_allow_html=True)
        return
    decision = result.get("policy_decision", result)
    decision_name = str(decision.get("decision", "")).upper() if isinstance(decision, dict) else ""
    risk_score = decision.get("risk_score") if isinstance(decision, dict) else None
    label = risk_label_for_result(result)
    st.markdown(
        f"""
        <div class='card'>
            <div class='meta-label'>CURRENT RISK</div>
            <div class='decision-text' style='color:var(--{'green' if decision_name == 'ALLOW' else 'red' if decision_name == 'BLOCK' else 'amber' if decision_name == 'ASK' else 'text'});'>{label}</div>
            <div class='meta-value'><strong>Risk Score:</strong> {risk_score if risk_score is not None else 'Not available'}</div>
            <div class='meta-value'><strong>Decision:</strong> {decision_name or 'Not available'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_transaction_result(result, "current_risk")


def render_policy_page():
    render_page_header("Policy Enforcement", "Deterministic controls that authorize AI-proposed transactions")
    st.markdown(
        """
        <div class='card'>
            <h3>🛡️ Policy Enforcement</h3>
            <div class='status-pill'><span class='dot'></span>ON</div>
            <div class='meta-value'>All transactions are monitored and evaluated against the user's authorization before payment.</div>
            <div class='meta-label'>Controls</div>
            <div class='meta-value'>Maximum amount · category · color · size · subscription · add-on · daily/session limits · aggregate/split detection</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_page():
    render_page_header()
    render_ai_buyer_section()
    render_ask_demo()


current_page = render_sidebar_navigation()

if current_page == "Dashboard Status":
    render_dashboard_page()
elif current_page == "Policy Enforcement":
    render_policy_page()
elif current_page == "Current Risk":
    render_current_risk_page()
elif current_page == "Audit Trail":
    render_page_header("Audit Trail", "Recent transaction history and audit records")
    render_audit_trail(audit_records())
elif current_page == "Demo / Testing":
    render_page_header("Demo / Testing", "Run predefined security scenarios")
    render_demo_scenarios()

st.markdown(
    "<div class='footer-note'>"
    "Agent Leash ensures AI agents follow user instructions, prevent unauthorized spending, and keep every transaction transparent and secure."
    "</div>",
    unsafe_allow_html=True,
)
