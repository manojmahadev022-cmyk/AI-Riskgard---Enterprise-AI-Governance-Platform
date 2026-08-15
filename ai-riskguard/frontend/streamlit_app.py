import streamlit as st
import httpx

# ─────────────────────────────────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI RiskGuard — Governance Assessment Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main-header {
        font-size: 2.2rem; font-weight: 700;
        background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header { font-size: 1.05rem; color: #4B5563; margin-bottom: 1.2rem; }

    .risk-badge-low { background:#D1FAE5; color:#065F46; padding:.35rem .8rem;
        border-radius:.375rem; font-weight:700; font-size:1.1rem; display:inline-block; }
    .risk-badge-moderate { background:#FEF3C7; color:#92400E; padding:.35rem .8rem;
        border-radius:.375rem; font-weight:700; font-size:1.1rem; display:inline-block; }
    .risk-badge-high { background:#FFEDD5; color:#C2410C; padding:.35rem .8rem;
        border-radius:.375rem; font-weight:700; font-size:1.1rem; display:inline-block; }
    .risk-badge-very-high { background:#FEE2E2; color:#991B1B; padding:.35rem .8rem;
        border-radius:.375rem; font-weight:700; font-size:1.1rem; display:inline-block; }

    .source-card {
        background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: .5rem;
        padding: .8rem 1rem; margin-bottom: .5rem;
    }
    .evidence-card {
        background: #EFF6FF; border-left: 3px solid #3B82F6;
        padding: .7rem 1rem; border-radius: 0 .375rem .375rem 0; margin-bottom: .5rem;
        font-size: .9rem;
    }
    .conflict-card {
        background: #FFF7ED; border-left: 3px solid #F59E0B;
        padding: .7rem 1rem; border-radius: 0 .375rem .375rem 0; margin-bottom: .5rem;
        font-size: .9rem;
    }
    .badge-law { background:#DCFCE7; color:#166534; padding:.15rem .5rem;
        border-radius:.25rem; font-size:.75rem; font-weight:600; }
    .badge-regulatory { background:#DBEAFE; color:#1E40AF; padding:.15rem .5rem;
        border-radius:.25rem; font-size:.75rem; font-weight:600; }
    .badge-standard { background:#F3E8FF; color:#6B21A8; padding:.15rem .5rem;
        border-radius:.25rem; font-size:.75rem; font-weight:600; }
    .badge-vendor { background:#FEF9C3; color:#854D0E; padding:.15rem .5rem;
        border-radius:.25rem; font-size:.75rem; font-weight:600; }
    .badge-general { background:#F1F5F9; color:#475569; padding:.15rem .5rem;
        border-radius:.25rem; font-size:.75rem; font-weight:600; }

    .confidence-high { color: #065F46; font-weight: 700; }
    .confidence-medium { color: #92400E; font-weight: 700; }
    .confidence-low { color: #C2410C; font-weight: 700; }
    .confidence-insufficient { color: #991B1B; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/color/96/shield.png", width=60)
st.sidebar.title("AI RiskGuard")
st.sidebar.markdown("**Enterprise AI Governance Platform**")
st.sidebar.markdown("---")
backend_url = st.sidebar.text_input("Backend API URL", value="http://localhost:8000")

backend_status = "Disconnected"
db_status = "Unknown"
version = "N/A"
try:
    with httpx.Client(timeout=3.0) as client:
        resp = client.get(f"{backend_url}/api/v1/health")
        if resp.status_code == 200:
            data = resp.json()
            backend_status = data.get("status", "healthy").capitalize()
            db_status = data.get("database", "connected").capitalize()
            version = data.get("version", "0.3.0")
except Exception:
    pass

if backend_status == "Healthy":
    st.sidebar.success(f"🟢 API Connected (v{version})")
    st.sidebar.info(f"💾 DB: {db_status}")
else:
    st.sidebar.error("🔴 Backend Server Offline")

st.sidebar.markdown("---")
st.sidebar.caption("MODUS AI Challenge — Step 3: Research + Evidence + RAG")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">🛡️ AI RiskGuard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Enterprise AI Governance · 10-Dimension Assessment · Research-Backed Evidence</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_research, tab_basic, tab_history, tab_config = st.tabs([
    "🔬 Research & Assess",
    "⚡ Quick Assessment",
    "📜 Assessment History",
    "⚙️ Framework",
])


# ─────────────────────────────────────────────────────────────────────────────
# Helper: source type badge HTML
# ─────────────────────────────────────────────────────────────────────────────
_SOURCE_BADGE_MAP = {
    "LAW_REGULATION": ("badge-law", "⚖️ Law / Regulation"),
    "REGULATORY_GUIDANCE": ("badge-regulatory", "🏛️ Regulatory Guidance"),
    "INDUSTRY_STANDARD": ("badge-standard", "📋 Industry Standard"),
    "VENDOR_INFORMATION": ("badge-vendor", "🏢 Vendor Information"),
    "GENERAL_WEB_CONTENT": ("badge-general", "🌐 General Web"),
}

def source_badge(source_type: str) -> str:
    css, label = _SOURCE_BADGE_MAP.get(source_type, ("badge-general", source_type))
    return f'<span class="{css}">{label}</span>'

def credibility_stars(level: int) -> str:
    return "⭐" * (level or 0) + "☆" * max(0, 5 - (level or 0))

def confidence_html(conf: str) -> str:
    cls = f"confidence-{conf.lower()}"
    return f'<span class="{cls}">{conf}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Research & Assess
# ─────────────────────────────────────────────────────────────────────────────
with tab_research:
    st.header("🔬 Research & Assess")
    st.markdown(
        "Runs real web research → extracts evidence from public sources → "
        "runs the governance assessment engine → returns evidence-backed results."
    )

    col_form, col_result = st.columns([1, 1], gap="large")

    with col_form:
        st.subheader("📋 AI Use Case Details")
        with st.form("research_assess_form"):
            r_name = st.text_input("AI Use Case Name *", placeholder="e.g. AI Recruitment Screening")
            r_industry = st.selectbox(
                "Industry Sector *",
                ["Human Resources", "Financial Services", "Healthcare", "Insurance",
                 "Retail & E-commerce", "Legal & Judicial", "Manufacturing & Supply Chain",
                 "Customer Service", "Education", "Other"],
            )
            r_description = st.text_area("Description *", placeholder="Describe the AI system...")
            r_purpose = st.text_area("Business Purpose *", placeholder="What operational goal does this AI serve?")
            r_data_used = st.text_area("Data Types Processed *", placeholder="CVs, financial records, PII...")
            r_human = st.selectbox(
                "Human Involvement Level *",
                [
                    "Human-in-the-loop (Human approves final decision)",
                    "Human-on-the-loop (Monitoring & exception overrides only)",
                    "Human-out-of-the-loop (Fully automated execution)",
                ],
            )
            research_btn = st.form_submit_button(
                "🔬 Research & Assess", width="stretch", type="primary"
            )

    with col_result:
        st.subheader("📊 Research-Backed Assessment Output")

        if research_btn:
            if not all([r_name.strip(), r_description.strip(), r_purpose.strip(), r_data_used.strip()]):
                st.error("Please fill in all required fields.")
            else:
                with st.spinner("🔍 Researching public sources… This may take 30–60 seconds."):
                    try:
                        with httpx.Client(timeout=120.0) as client:
                            # Create use case
                            uc_payload = {
                                "name": r_name, "description": r_description,
                                "industry": r_industry, "purpose": r_purpose,
                                "data_used": r_data_used, "human_involvement": r_human,
                            }
                            uc_res = client.post(f"{backend_url}/api/v1/use-cases", json=uc_payload)
                            if uc_res.status_code != 201:
                                st.error(f"Failed to create use case: {uc_res.text}")
                                st.stop()

                            uc_id = uc_res.json()["id"]

                            # Research-backed assessment
                            eval_res = client.post(
                                f"{backend_url}/api/v1/assessments/{uc_id}/research-backed",
                                timeout=120.0,
                            )
                            if eval_res.status_code == 201:
                                st.session_state["research_assessment"] = eval_res.json()
                                st.success(f"✅ Research & Assessment complete for **{r_name}**!")
                            else:
                                st.error(f"Assessment error ({eval_res.status_code}): {eval_res.text}")
                    except Exception as ex:
                        st.error(f"Cannot connect to backend: {ex}")

        # ── Display research-backed result ────────────────────────────────────
        if "research_assessment" in st.session_state:
            ra = st.session_state["research_assessment"]
            rs = ra.get("research_status", {})
            overall_score = ra["overall_score"]
            risk_level = ra["risk_level"]
            dims = ra.get("dimensions", [])

            # ── A. Overall Assessment ─────────────────────────────────────────
            st.markdown("---")
            st.subheader("A. Overall Assessment")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Governance Score", f"{overall_score} / 5.0")
            with m2:
                badge_css = f"risk-badge-{risk_level.lower().replace(' ', '-')}"
                st.markdown("**Risk Level:**")
                st.markdown(f'<div class="{badge_css}">{risk_level}</div>', unsafe_allow_html=True)
            with m3:
                st.metric("Dimensions with Evidence", rs.get("dimensions_supported", 0))
            with m4:
                st.metric("Evidence Items", rs.get("evidence_extracted", 0))

            # ── E. Research Status ────────────────────────────────────────────
            with st.expander("📡 E. Research Pipeline Status", expanded=False):
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("Queries Generated", rs.get("queries_generated", 0))
                sc2.metric("URLs Found", rs.get("sources_found", 0))
                sc3.metric("Sources Fetched", rs.get("sources_fetched", 0))
                sc4.metric("Conflicts Detected", rs.get("conflicts_detected", 0))

            # ── B. Governance Dimensions ──────────────────────────────────────
            st.markdown("---")
            st.subheader("B. Governance Dimensions")
            for dim in dims:
                d_name = dim["dimension"]
                d_score = dim["score"]
                d_reasoning = dim["reasoning"]
                d_conf = dim.get("evidence_confidence", "INSUFFICIENT")
                d_ev_count = dim.get("evidence_count", 0)

                score_ratio = (d_score - 1.0) / 4.0
                conf_html = confidence_html(d_conf)

                with st.expander(
                    f"**{d_name}** — Score: `{d_score}/5.0`  |  Evidence: {d_ev_count} items  |  Confidence: {d_conf}",
                    expanded=False,
                ):
                    st.progress(score_ratio)
                    st.caption(f"**Reasoning:** {d_reasoning}")
                    st.markdown(f"**Evidence Confidence:** {conf_html}", unsafe_allow_html=True)

                    evidence_list = dim.get("evidence", [])
                    if evidence_list:
                        st.markdown("**Supporting Evidence:**")
                        for ev in evidence_list:
                            card_class = "conflict-card" if ev.get("conflict_flag") else "evidence-card"
                            conflict_label = " ⚠️ *Conflicting information detected*" if ev.get("conflict_flag") else ""
                            src_badge = source_badge(ev.get("source_type", "GENERAL_WEB_CONTENT"))
                            cred = credibility_stars(ev.get("credibility_level", 1))
                            title = ev.get("source_title") or "Unknown Source"
                            url = ev.get("url", "")
                            pub = ev.get("publisher", "")
                            text = ev.get("text", "")
                            url_link = f'<a href="{url}" target="_blank">{url}</a>' if url else "N/A"
                            st.markdown(
                                f'<div class="{card_class}">'
                                f'<b>{title}</b>{conflict_label}<br>'
                                f'{src_badge} &nbsp; Credibility: {cred} &nbsp; Publisher: {pub}<br>'
                                f'🔗 {url_link}<br>'
                                f'<i>"{text}"</i>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.info("Insufficient evidence found for this dimension from retrieved sources.")

            # ── C. Supporting Evidence (all) ──────────────────────────────────
            with st.expander("C. 📚 All Supporting Evidence", expanded=False):
                all_ev = [ev for dim in dims for ev in dim.get("evidence", [])]
                if all_ev:
                    for ev in all_ev:
                        card_class = "conflict-card" if ev.get("conflict_flag") else "evidence-card"
                        src_badge = source_badge(ev.get("source_type", "GENERAL_WEB_CONTENT"))
                        url = ev.get("url", "")
                        url_link = f'<a href="{url}" target="_blank">{url}</a>' if url else "N/A"
                        st.markdown(
                            f'<div class="{card_class}">'
                            f'<b>[{ev.get("dimension","?")}]</b> {ev.get("source_title","Unknown")} '
                            f'{src_badge}<br>🔗 {url_link}<br>'
                            f'<i>"{ev.get("text","")}"</i>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.info("No evidence was retrieved for this assessment.")

            # ── D. Research Sources Table ─────────────────────────────────────
            with st.expander("D. 🌐 Research Sources", expanded=False):
                uc_id_display = ra.get("assessment_id")
                try:
                    with httpx.Client(timeout=10.0) as client:
                        # get use_case_id from the nested data
                        all_dims = ra.get("dimensions", [])
                        all_src_urls = list({
                            ev.get("url") for dim in all_dims
                            for ev in dim.get("evidence", [])
                            if ev.get("url")
                        })
                        if all_src_urls:
                            import pandas as pd
                            rows = []
                            for dim in all_dims:
                                for ev in dim.get("evidence", []):
                                    rows.append({
                                        "Source": ev.get("source_title", "Unknown"),
                                        "Publisher": ev.get("publisher", ""),
                                        "Type": ev.get("source_type", ""),
                                        "Credibility": credibility_stars(ev.get("credibility_level", 1)),
                                        "URL": ev.get("url", ""),
                                    })
                            if rows:
                                import pandas as pd
                                df = pd.DataFrame(rows).drop_duplicates(subset=["URL"])
                                st.dataframe(df, width="stretch", hide_index=True)
                        else:
                            st.info("No sources retrieved.")
                except Exception:
                    st.info("Sources table unavailable.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Quick Assessment (Step 2 deterministic — preserved unchanged)
# ─────────────────────────────────────────────────────────────────────────────
with tab_basic:
    st.header("⚡ Quick Governance Assessment")
    st.write("Deterministic rule-based scoring across 10 dimensions. No external research.")

    col_form2, col_result2 = st.columns([1, 1], gap="large")

    with col_form2:
        st.subheader("📋 Use Case Input Details")
        with st.form("use_case_assessment_form"):
            name = st.text_input("AI Use Case Name *", value="AI Recruitment Screening System")
            industry = st.selectbox(
                "Industry Sector *",
                ["Human Resources", "Financial Services", "Healthcare", "Insurance",
                 "Retail & E-commerce", "Legal & Judicial", "Manufacturing & Supply Chain",
                 "Customer Service", "Other"],
            )
            description = st.text_area(
                "Description *",
                value="AI ranks and screens job applicants based on resume content, assessment scores, and work history.",
            )
            purpose = st.text_area("Business Purpose *", value="Improve recruitment efficiency and automate initial applicant screening.")
            data_used = st.text_area("Data Types Processed *", value="Resume text, employment history, candidate assessment results, PII.")
            human_involvement = st.selectbox(
                "Human Involvement Level *",
                [
                    "Human-in-the-loop (Recruiter/Human approves final decision)",
                    "Human-on-the-loop (Monitoring & exception overrides only)",
                    "Human-out-of-the-loop (Fully automated execution)",
                ],
            )
            run_button = st.form_submit_button("Run Governance Assessment", width="stretch")

    with col_result2:
        st.subheader("📊 Assessment Output")
        if run_button:
            if not name or not description or not purpose or not data_used:
                st.error("Please fill in all required fields.")
            else:
                with st.spinner("Processing governance assessment..."):
                    try:
                        with httpx.Client(timeout=15.0) as client:
                            uc_payload = {
                                "name": name, "description": description,
                                "industry": industry, "purpose": purpose,
                                "data_used": data_used, "human_involvement": human_involvement,
                            }
                            uc_res = client.post(f"{backend_url}/api/v1/use-cases", json=uc_payload)
                            if uc_res.status_code == 201:
                                uc_id = uc_res.json()["id"]
                                eval_res = client.post(f"{backend_url}/api/v1/assessments/{uc_id}")
                                if eval_res.status_code == 201:
                                    st.session_state["latest_assessment"] = eval_res.json()
                                    st.success(f"Assessment completed for **{name}**!")
                                else:
                                    st.error(f"Assessment error: {eval_res.text}")
                            else:
                                st.error(f"Failed to register use case: {uc_res.text}")
                    except Exception as ex:
                        st.error(f"Cannot connect to backend: {ex}")

        if "latest_assessment" in st.session_state:
            assessment = st.session_state["latest_assessment"]
            overall_score = assessment["overall_score"]
            risk_level = assessment["risk_level"]
            dims = assessment["dimensions"]
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Overall Governance Score", f"{overall_score} / 5.0")
            with m2:
                badge_class = f"risk-badge-{risk_level.lower().replace(' ', '-')}"
                st.markdown("**Overall Risk Level:**")
                st.markdown(f'<div class="{badge_class}">{risk_level}</div>', unsafe_allow_html=True)
            st.markdown("---")
            st.subheader("10 Governance Dimension Breakdown")
            for dim in dims:
                st.markdown(f"**{dim['dimension']}**: `{dim['score']} / 5.0`")
                st.progress((dim["score"] - 1.0) / 4.0)
                st.caption(f"**Reasoning:** {dim['reasoning']}")
                st.markdown("")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Assessment History
# ─────────────────────────────────────────────────────────────────────────────
with tab_history:
    st.header("📜 Governance Assessment Log")
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{backend_url}/api/v1/assessments")
            if res.status_code == 200:
                history = res.json()
                if not history:
                    st.info("No assessments conducted yet.")
                else:
                    for item in history:
                        with st.expander(
                            f"Assessment #{item['id']} — Score: {item['overall_score']} ({item['risk_level']})"
                        ):
                            st.write(f"**Use Case ID:** `{item['use_case_id']}`")
                            st.write(f"**Date:** {item['created_at']}")
                            if st.button("View Full Details", key=f"hist_{item['id']}"):
                                detail_res = client.get(f"{backend_url}/api/v1/assessments/{item['id']}")
                                if detail_res.status_code == 200:
                                    st.json(detail_res.json())
    except Exception:
        st.warning("Backend API offline.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: Framework Configuration
# ─────────────────────────────────────────────────────────────────────────────
with tab_config:
    st.header("⚙️ Framework Configuration")
    st.markdown("""
    **Risk Level Thresholds (1.00 – 5.00 Scale):**
    - `1.00 – 1.99`: **LOW**
    - `2.00 – 2.99`: **MODERATE**
    - `3.00 – 3.99`: **HIGH**
    - `4.00 – 5.00`: **VERY HIGH**

    **Source Type Credibility:**
    | Source Type | Credibility |
    |---|---|
    | Law / Regulation | ⭐⭐⭐⭐⭐ |
    | Regulatory Guidance | ⭐⭐⭐⭐ |
    | Industry Standard | ⭐⭐⭐⭐ |
    | Vendor Information | ⭐⭐ |
    | General Web Content | ⭐ |

    **Evidence Confidence Levels:**
    - **HIGH** — 3+ items, at least one regulatory/standards source
    - **MEDIUM** — 2+ items from any source
    - **LOW** — 1 item from any source
    - **INSUFFICIENT** — No evidence found for this dimension

    **Dimension Weights:** All 10 dimensions use equal weight (`1.0`).
    Adjustable in `backend/core/governance_config.py`.
    """)
