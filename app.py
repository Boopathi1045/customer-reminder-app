import os
import requests
import streamlit as st
from dotenv import load_dotenv

# ── ENV / CONFIG ─────────────────────────────────────────────
# load_dotenv()
# API_BASE = os.getenv(
#     "API_BASE",
#     "https://ac3a284a-00b5-4e42-917a-b5feb1008c52-00-9bges9mc4cdd.sisko.replit.dev",  # <-- swap to your URL
# )
load_dotenv()
API_BASE = os.getenv(
    "API_BASE",
    "https://rboopathi1045.pythonanywhere.com",  # <-- swap to your URL
)

st.set_page_config(page_title="Customer Manager", page_icon="📋", layout="wide")
st.title("📋 Customer Sheet Manager")

# ── Add Customer ────────────────────────────────────────────
with st.expander("➕ Add New Customer"):
    name = st.text_input("Name")
    phone = st.text_input("Phone Number")
    paid_flag = st.radio("Paid?", ["Yes", "No"], horizontal=True)

    if st.button("Add Customer"):
        if not name or not phone:
            st.warning("Please enter both name and phone number.")
        else:
            try:
                res = requests.post(
                    f"{API_BASE}/add",
                    json={"name": name, "phone": phone, "paid": paid_flag.lower()},
                    timeout=8,
                )
                if res.ok:
                    st.success("✅ Added!")
                else:
                    st.error(res.text)
            except Exception as e:
                st.error(e)

st.divider()

# ── Session State ───────────────────────────────────────────
if "show_list" not in st.session_state:
    st.session_state.show_list = False
if "filter_status" not in st.session_state:
    st.session_state.filter_status = "All"
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None  # row currently in edit‑mode

# ── Primary Controls ────────────────────────────────────────
col_sh, col_hd = st.columns([1, 1])
with col_sh:
    if st.button("📋 Show List"):
        st.session_state.show_list = True
with col_hd:
    if st.button("🙈 Hide List"):
        st.session_state.show_list = False

# ── Filters Row ─────────────────────────────────────────────
if st.session_state.show_list:
    col_flt, col_srh, col_clr = st.columns([2, 3, 1])

    with col_flt:
        new_filter = st.selectbox(
            "Filter by Status",
            ["All", "Paid", "Unpaid"],
            index=["All", "Paid", "Unpaid"].index(st.session_state.filter_status),
        )
        if new_filter != st.session_state.filter_status:
            st.session_state.filter_status = new_filter

    with col_srh:
        s = st.text_input(
            "🔍 Search Name", value=st.session_state.search_query, placeholder="Type name…"
        ).strip()
        if s != st.session_state.search_query:
            st.session_state.search_query = s

    with col_clr:
        st.markdown("<p style='margin-bottom:2px;'>Clear Filters</p>", unsafe_allow_html=True)
        if st.button("❌ Clear"):
            st.session_state.filter_status = "All"
            st.session_state.search_query = ""
            st.session_state.edit_idx = None

    # ── Fetch & Render List ─────────────────────────────────
    try:
        response = requests.get(f"{API_BASE}/list", timeout=10)
        response.raise_for_status()
        rows = response.json()
    except Exception as e:
        st.error(f"Fetch error: {e}")
        rows = []

    # Apply filters
    display_rows = []
    for idx, row in enumerate(rows):
        name = row.get("Name", "")
        status = row.get("Status", "not paid").lower()
        if st.session_state.filter_status == "Paid" and status != "paid":
            continue
        if st.session_state.filter_status == "Unpaid" and status == "paid":
            continue
        if st.session_state.search_query and st.session_state.search_query not in name.lower():
            continue
        display_rows.append((idx, row))

    # Helper: call backend
    def _api_post(endpoint: str, payload: dict):
        try:
            res = requests.post(f"{API_BASE}/{endpoint}", json=payload, timeout=8)
            if not res.ok:
                st.error(f"API error: {res.text}")
        except Exception as exc:
            st.error(exc)

    # Render each row
    for idx, row in display_rows:
        st.markdown("---")
        name = row["Name"]
        phone = row["Phone"]
        status = row["Status"].lower()
        last = row["LastPaid"] or "—"

        edit_mode = st.session_state.edit_idx == idx
        if edit_mode:
            # ── EDIT UI ───────────────────────────────────────
            with st.form(f"edit_form_{idx}"):
                new_name = st.text_input("Name", value=name)
                new_phone = st.text_input("Phone", value=phone)
                new_status = st.selectbox("Status", ["paid", "not paid"], index=0 if status == "paid" else 1)
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("💾 Save"):
                        _api_post("update", {
                            "original_name": name,
                            "name": new_name,
                            "phone": new_phone,
                            "status": new_status,
                        })
                        st.session_state.edit_idx = None
                        st.rerun()
                with c2:
                    if st.form_submit_button("✖️ Cancel"):
                        st.session_state.edit_idx = None
                        st.rerun()
        else:
            # ── READ‑ONLY ROW ────────────────────────────────
            st.markdown(f"**{name}**  |  📞 `{phone}`", unsafe_allow_html=True)
            if status == "paid":
                st.success(f"✅ Paid on {last}")
            else:
                st.error("❌ Not Paid")

            # Row action buttons
            act_col1, act_col2, act_col3 = st.columns([1, 1, 1])
            with act_col1:
                if st.button("✏️ Edit", key=f"editbtn_{idx}"):
                    st.session_state.edit_idx = idx
                    st.rerun()
            with act_col2:
                toggle_label = "Mark Unpaid" if status == "paid" else "Mark Paid"
                if st.button(toggle_label, key=f"toggle_{idx}"):
                    _api_post("toggle_paid", {"name": name})
                    st.rerun()
            with act_col3:
                if st.button("🗑️ Delete", key=f"del_{idx}"):
                    _api_post("delete", {"name": name})
                    st.rerun()
