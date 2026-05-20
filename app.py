import sys
import streamlit as st

sys.path.append("data")  # for tickets module

from agents.intake_agent import parse_query
from agents.retrieval_agent import retrieve_filtered
from agents.risk_agent import analyze_risks, get_overall_severity
from agents.critic_agent import validate_findings

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Delivery Control Tower",
    page_icon="🗼",
    layout="wide"
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .severity-critical { 
        background: #ff4444; color: white; 
        padding: 4px 12px; border-radius: 4px; 
        font-weight: bold; font-size: 14px;
    }
    .severity-high { 
        background: #ff8800; color: white; 
        padding: 4px 12px; border-radius: 4px; 
        font-weight: bold; font-size: 14px;
    }
    .severity-medium { 
        background: #ffcc00; color: black; 
        padding: 4px 12px; border-radius: 4px; 
        font-weight: bold; font-size: 14px;
    }
    .severity-low { 
        background: #44aa44; color: white; 
        padding: 4px 12px; border-radius: 4px; 
        font-weight: bold; font-size: 14px;
    }
    .agent-trace {
        background: #1e1e2e; color: #cdd6f4;
        padding: 12px; border-radius: 8px;
        font-family: monospace; font-size: 13px;
    }
    .ticket-card {
        background: #2a2a3e; color: #cdd6f4;
        padding: 10px; border-radius: 6px;
        margin: 4px 0; font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

if "tickets_loaded" not in st.session_state:
    with st.spinner("Loading tickets from Jira..."):
        from tickets import get_all_tickets
        st.session_state.all_tickets = get_all_tickets()
        st.session_state.tickets_loaded = True

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🗼 Agentic Delivery Control Tower")
st.caption("Governed multi-agent enterprise workflow system — SmartShoe Project")
st.divider()

# ---------------------------------------------------------------------------
# Sidebar — agent trace + query history
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🤖 Agent Pipeline")
    st.caption("Execution trace from last query")

    if st.session_state.history:
        last = st.session_state.history[-1]
        trace = last.get("trace", [])

        for step in trace:
            icon = "✅" if step["status"] == "success" else "⚠️"
            st.markdown(f"""
            <div class="agent-trace">
            {icon} <b>{step['agent']}</b><br>
            {step['detail']}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")

    st.divider()
    st.header("📋 Query History")
    for i, h in enumerate(reversed(st.session_state.history)):
        if st.button(f"↩ {h['query'][:40]}...", key=f"history_{i}"):
            pass

# ---------------------------------------------------------------------------
# Main — query input
# ---------------------------------------------------------------------------
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input(
        "Ask about your project",
        placeholder="e.g. What are the biggest risks this sprint?",
        label_visibility="collapsed"
    )
with col2:
    run_btn = st.button("Analyze →", type="primary", use_container_width=True)

# Example queries
st.caption("Try: &nbsp; _What are the biggest risks?_ &nbsp;|&nbsp; _Show me blocked tickets_ &nbsp;|&nbsp; _Who is overloaded?_ &nbsp;|&nbsp; _Overall project health?_")

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------
if run_btn and query:
    trace = []

    with st.spinner("Running agent pipeline..."):

        # Step 1: Intake
        parsed = parse_query(query)
        trace.append({
            "agent": "Intake Agent",
            "status": "success",
            "detail": f"Intent: {parsed['intent']} | Urgency: {parsed['urgency']}"
        })

        # Step 2: Retrieval
        results = retrieve_filtered(
            parsed['search_query'],
            filters=parsed['filters'] or None
        )
        tickets = [r['ticket'] for r in results]
        trace.append({
            "agent": "Retrieval Agent",
            "status": "success",
            "detail": f"Retrieved {len(tickets)} tickets | Top score: {results[0]['score'] if results else 0}"
        })

        # Step 3: Risk Analysis
        findings = analyze_risks(tickets)
        trace.append({
            "agent": "Risk Analysis Agent",
            "status": "success",
            "detail": f"Generated {len(findings)} findings"
        })

        # Step 4: Critic
        validated, flagged = validate_findings(findings, tickets)
        trace.append({
            "agent": "Critic Agent",
            "status": "success",
            "detail": f"{len(validated)}/{len(findings)} findings validated | {len(flagged)} flagged"
        })

        severity = get_overall_severity(validated)

        # Save to history
        st.session_state.history.append({
            "query": query,
            "parsed": parsed,
            "tickets": tickets,
            "findings": validated,
            "flagged": flagged,
            "severity": severity,
            "trace": trace
        })

    st.rerun()

# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------
if st.session_state.history:
    last = st.session_state.history[-1]

    # Overall health banner
    sev = last["severity"]
    sev_class = f"severity-{sev.lower()}"
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
        <span style="font-size:18px; font-weight:600;">Overall Project Health:</span>
        <span class="{sev_class}">{sev}</span>
    </div>
    """, unsafe_allow_html=True)

    # Two columns: findings + tickets
    left, right = st.columns([3, 2])

    with left:
        st.subheader("🔍 Risk Findings")

        if last["flagged"]:
            with st.expander(f"⚠️ Critic flagged {len(last['flagged'])} issue(s)"):
                for flag in last["flagged"]:
                    st.warning(flag)

        for f in last["findings"]:
            sev_class = f"severity-{f['severity'].lower()}"
            with st.expander(
                f"[{f['severity']}] {f['risk']} — confidence {f['confidence']}",
                expanded=True
            ):
                st.markdown(f"**Evidence tickets:** {', '.join(f['evidence'])}")
                st.markdown(f"**Detail:** {f['detail']}")

    with right:
        st.subheader("🎫 Retrieved Tickets")
        for t in last["tickets"]:
            status_color = {
                "Blocked": "🔴",
                "In Review": "🟡",
                "To Do": "🔵",
                "Done": "🟢"
            }.get(t["status"], "⚪")

            st.markdown(f"""
            <div class="ticket-card">
            {status_color} <b>{t['id']}</b> — {t['title']}<br>
            <small>Priority: {t['priority']} | Assignee: {t['assignee'] or 'Unassigned'} | Status: {t['status']}</small>
            </div>
            """, unsafe_allow_html=True)