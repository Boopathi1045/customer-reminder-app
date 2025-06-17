import os
import requests
import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from streamlit_authenticator import Hasher, Authenticate

# Load environment variables
load_dotenv()
API_BASE = os.getenv("API_BASE", "https://your-default-api-url.com")

# --- User Authentication ---
names = ["Admin"]
usernames = ["admin"]
passwords = ["password123"]  # change as needed

# Hash the passwords list
hashed_passwords = Hasher(passwords).generate()

authenticator = Authenticate(
    names, usernames, hashed_passwords,
    "customer_app", "auth_cookie", cookie_expiry_days=1
)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status is False:
    st.error("❌ Incorrect username or password")
elif authentication_status is None:
    st.warning("👤 Please enter your username and password")
elif authentication_status:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"✅ Logged in as {name}")

    st.set_page_config(page_title="Customer Manager", page_icon="📋", layout="wide")
    st.title("📋 Customer Sheet Manager")

    # ------------- Add Customer ------------------------------------------
    with st.expander("➕ Add New Customer"):
        a_name = st.text_input("Name")
        a_phone = st.text_input("Phone Number")
        a_paid = st.radio("Paid?", ["Yes", "No"], horizontal=True)
        if st.button("Add Customer"):
            if not a_name or not a_phone:
                st.warning("Both fields required.")
            else:
                res = requests.post(f"{API_BASE}/add",
                                    json={"name": a_name, "phone": a_phone, "paid": a_paid.lower()})
                st.success("Added!" if res.ok else res.text)
                st.rerun()

    st.divider()

    # -------- Session defaults -------------------------------------------
    for key, val in {"show_list": False, "filter_status": "All", "search_query": "", "edit_idx": None}.items():
        st.session_state.setdefault(key, val)

    # -------- Controls ---------------------------------------------------
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("📋 Show List"):
        st.session_state.show_list = True
    if btn_col2.button("🙈 Hide List"):
        st.session_state.show_list = False

    if not st.session_state.show_list:
        st.stop()

    # -------- Filters ----------------------------------------------------
    f_col, s_col, c_col = st.columns([2, 3, 1])
    with f_col:
        filt = st.selectbox("Filter", ["All", "Paid", "Unpaid"], index=["All","Paid","Unpaid"].index(st.session_state.filter_status))
        st.session_state.filter_status = filt
    with s_col:
        st.session_state.search_query = st.text_input("🔍 Search Name", st.session_state.search_query)
    with c_col:
        st.markdown("Clear\n")
        if st.button("❌"):
            st.session_state.filter_status = "All"
            st.session_state.search_query = ""

    # -------- Fetch sheet ------------------------------------------------
    rows = requests.get(f"{API_BASE}/list").json()

    def date_or_none(iso):
        return date.fromisoformat(iso) if iso else None

    # -------- Display rows -----------------------------------------------
    for idx, row in enumerate(rows):
        name, phone = row["Name"], row["Phone"]
        status = row["Status"].lower()
        last_paid = row["LastPaid"]
        next_pay = row.get("NextPayment", "")

        if st.session_state.filter_status == "Paid" and status != "paid": continue
        if st.session_state.filter_status == "Unpaid" and status == "paid": continue
        if st.session_state.search_query and st.session_state.search_query not in name.lower(): continue

        st.markdown("---")
        editing = st.session_state.edit_idx == idx

        if editing:
            with st.form(f"edit_form_{idx}"):
                ename = st.text_input("Name", value=name)
                ephone = st.text_input("Phone", value=phone)
                estatus = st.selectbox("Status", ["paid","not paid"], index=0 if status=="paid" else 1)
                elast = st.date_input("Last Paid", value=date_or_none(last_paid) or date.today())
                enext = st.date_input("Next Payment", value=date_or_none(next_pay) or (date.today()+relativedelta(months=1)))
                save, cancel = st.columns(2)
                with save:
                    if st.form_submit_button("💾 Save"):
                        requests.post(f"{API_BASE}/update", json={
                            "original_name": name,
                            "name": ename,
                            "phone": ephone,
                            "status": estatus,
                            "last_paid": elast.isoformat() if estatus=="paid" else "",
                            "next_payment": enext.isoformat() if estatus=="paid" else ""
                        })
                        st.session_state.edit_idx = None
                        st.rerun()
                with cancel:
                    if st.form_submit_button("✖️ Cancel"):
                        st.session_state.edit_idx = None
                        st.rerun()
        else:
            st.markdown(f"**{name}** | 📞 `{phone}`")
            if status == "paid":
                st.success(f"✅ Paid: {last_paid} | Next: {next_pay}")
            else:
                st.error("❌ Not Paid")

            c1,c2,c3 = st.columns(3)
            if c1.button("✏️ Edit", key=f"e{idx}"):
                st.session_state.edit_idx = idx
                st.rerun()
            if c2.button("Toggle Paid", key=f"t{idx}"):
                requests.post(f"{API_BASE}/toggle_paid", json={"name": name})
                st.rerun()
            if c3.button("🗑️ Del", key=f"d{idx}"):
                requests.post(f"{API_BASE}/delete", json={"name": name})
                st.rerun()
