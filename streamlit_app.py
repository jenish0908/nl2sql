import os
import httpx
import streamlit as st
import pandas as pd

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="NL2SQL Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🤖 NL2SQL Agent")
st.caption("Ask questions about your e-commerce data in plain English")


def fetch_summary() -> dict | None:
    try:
        resp = httpx.get(f"{API_URL}/evaluations/summary", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def fetch_history() -> list[dict]:
    try:
        resp = httpx.get(f"{API_URL}/history", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def submit_query(question: str) -> dict | None:
    try:
        resp = httpx.post(
            f"{API_URL}/query",
            json={"question": question},
            timeout=120,
        )
        return resp.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


def submit_clarify(question: str, clarification: str) -> dict | None:
    try:
        resp = httpx.post(
            f"{API_URL}/query/clarify",
            json={"question": question, "clarification": clarification},
            timeout=120,
        )
        return resp.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


def submit_feedback(query_id: int, sql_correct: bool, result_correct: bool, rating: int, comment: str):
    try:
        httpx.post(
            f"{API_URL}/evaluations/{query_id}/feedback",
            json={
                "sql_correct": sql_correct,
                "result_correct": result_correct,
                "rating": rating,
                "comment": comment,
            },
            timeout=10,
        )
    except Exception:
        pass


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📊 Evaluation Summary")
    summary = fetch_summary()
    if summary:
        st.metric("Total Queries", summary["total_queries"])
        st.metric("Avg Latency", f"{summary['avg_latency_ms']:.0f} ms")
        st.metric("Avg Cost", f"${summary['avg_cost_usd']:.4f}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Error Rate", f"{summary['error_rate']*100:.1f}%")
        with col2:
            st.metric("Correction Rate", f"{summary['self_correction_rate']*100:.1f}%")
    else:
        st.info("No data yet — ask a question!")

    st.divider()
    st.header("💡 Example Questions")
    examples = [
        "Which category had the highest revenue last month?",
        "Show me the top 5 customers by total order value",
        "Which products are running low on stock?",
        "What is the average order value by city?",
        "How many orders were placed last week by status?",
        "Which supplier has the highest rated products?",
        "Show total revenue per month for the last 3 months",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
            st.session_state["question_input"] = ex


# ── Main Query Input ──────────────────────────────────────────────────────────
default_question = st.session_state.get("question_input", "")
question = st.text_area(
    "Ask a question about your data",
    value=default_question,
    placeholder="e.g. Which city had the highest order value last month?",
    height=80,
    key="main_question",
)

col_submit, col_clear = st.columns([1, 5])
with col_submit:
    submit = st.button("🔍 Run Query", type="primary", use_container_width=True)
with col_clear:
    if st.button("Clear", use_container_width=False):
        st.session_state.pop("question_input", None)
        st.session_state.pop("last_result", None)
        st.session_state.pop("clarification_question", None)
        st.rerun()

# ── Handle Clarification Flow ─────────────────────────────────────────────────
if "clarification_question" in st.session_state:
    cq = st.session_state["clarification_question"]
    st.warning(f"**Clarification needed:** {cq['clarification_needed']}")
    with st.form("clarify_form"):
        clarification_text = st.text_input("Your clarification:")
        clarify_submit = st.form_submit_button("Submit Clarification")
    if clarify_submit and clarification_text:
        with st.spinner("Re-running with clarification..."):
            result = submit_clarify(cq["original_question"], clarification_text)
        if result:
            st.session_state["last_result"] = result
            del st.session_state["clarification_question"]
            st.rerun()

# ── Submit and Process ────────────────────────────────────────────────────────
if submit and question.strip():
    with st.spinner("Thinking... 🧠"):
        result = submit_query(question.strip())
    if result:
        st.session_state["last_result"] = result
        if "clarification_needed" in result and result["clarification_needed"]:
            st.session_state["clarification_question"] = result["clarification_needed"]
        st.rerun()

# ── Display Results ───────────────────────────────────────────────────────────
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    if result.get("error"):
        st.error(f"**Error:** {result['error']}")
    elif result.get("clarification_needed") and "clarification_question" in st.session_state:
        pass
    else:
        st.divider()

        # Metrics bar
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("⏱ Latency", f"{result['latency_ms']:.0f} ms")
        m2.metric("💰 Cost", f"${result['cost_usd']:.4f}")
        m3.metric("🔢 Tokens", f"{result['tokens_used']:,}")
        m4.metric("🔄 Corrections", result.get("self_corrections", 0))
        m5.metric("📋 Rows", result.get("row_count", 0))

        st.divider()

        # SQL and explanation
        col_sql, col_explain = st.columns([1, 1])
        with col_sql:
            st.subheader("Generated SQL")
            if result.get("sql"):
                st.code(result["sql"], language="sql")
        with col_explain:
            st.subheader("Explanation")
            if result.get("explanation"):
                st.write(result["explanation"])
            if result.get("intent"):
                intent = result["intent"]
                st.caption(
                    f"Intent: **{intent.get('intent_type', 'N/A')}** | "
                    f"Time: {intent.get('time_range') or 'none'}"
                )

        # Results table
        if result.get("results"):
            st.subheader(f"Results ({result['row_count']} rows)")
            df = pd.DataFrame(result["results"])
            st.dataframe(df, use_container_width=True)
        elif result.get("sql"):
            st.info("Query returned no results.")

        # Feedback
        with st.expander("📝 Rate this result"):
            with st.form(f"feedback_{result['query_id']}"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    sql_correct = st.checkbox("SQL is correct", value=True)
                    result_correct = st.checkbox("Results are correct", value=True)
                with col_f2:
                    rating = st.slider("Overall rating", 1, 5, 5)
                comment = st.text_input("Comment (optional)")
                if st.form_submit_button("Submit Feedback"):
                    submit_feedback(result["query_id"], sql_correct, result_correct, rating, comment)
                    st.success("Feedback recorded!")

# ── Query History ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("📜 Recent Queries")
history = fetch_history()
if history:
    display_history = history[:5]
    for item in display_history:
        with st.expander(f"#{item['id']} — {item['question'][:80]}..."):
            if item.get("sql"):
                st.code(item["sql"], language="sql")
            col_h1, col_h2, col_h3 = st.columns(3)
            col_h1.metric("Latency", f"{item.get('latency_ms', 0):.0f} ms")
            col_h2.metric("Cost", f"${item.get('cost_usd', 0):.4f}")
            col_h3.metric("Rows", item.get("row_count", 0))
else:
    st.info("No query history yet.")
