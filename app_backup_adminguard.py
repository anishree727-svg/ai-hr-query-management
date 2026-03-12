import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

from db import (
    ensure_tables,
    get_user,
    save_leave_request,
    get_all_leave_requests,
    update_leave_status,
    dashboard_counts,
)

st.set_page_config(page_title="HR Assistant", layout="wide")
ensure_tables()

# ---------- helpers ----------
def flash_show():
    if st.session_state.get("flash"):
        st.success(st.session_state["flash"])
        st.session_state["flash"] = None

def logout_box():
    role = st.session_state.get("role")
    user = st.session_state.get("username")
    if role:
        st.success(f"Logged in as {role} ({user})")
        if st.button("Logout"):
            for k in ("logged_in", "role", "username"):
                st.session_state.pop(k, None)
            st.session_state["flash"] = "You have been logged out."
            st.rerun()

def require_admin():
    if st.session_state.get("role") != "admin":
        st.error("Only admin can access this page.")
        st.stop()

# ---------- pages ----------
def page_login():
    st.title("HR Assistant — Login")
    flash_show()
    st.caption("Default credentials: admin/password123 or employee/emp123")
    u = st.text_input("Enter username")
    p = st.text_input("Enter password", type="password")
    if st.button("Login"):
        user = get_user(u.strip(), p.strip())
        if user:
            st.session_state.update(
                logged_in=True, role=user["role"], username=user["username"], flash=f"Welcome, {user['username']}!"
            )
            st.rerun()
        else:
            st.error("Invalid username or password")

def page_dashboard():
    st.header("Dashboard")
    flash_show()
    logout_box()
    counts = dashboard_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Requests", counts.get("total", 0))
    c2.metric("Approved", counts.get("approved", 0))
    c3.metric("Rejected", counts.get("rejected", 0))

    st.subheader("By Status")
    st.write(pd.DataFrame([
        {"status": "Pending", "count": counts.get("pending", 0)},
        {"status": "Approved", "count": counts.get("approved", 0)},
        {"status": "Rejected", "count": counts.get("rejected", 0)},
    ]))

def page_submit():
    st.header("Leave Request Form")
    flash_show()
    logout_box()
    with st.form("leave_form"):
        name = st.text_input("Your Name*")
        leave_type = st.selectbox("Leave Type*", ["Casual Leave", "Sick Leave", "Earned Leave"])
        days = st.number_input("Number of days*", 1, 30, 1)
        reason = st.text_area("Reason (optional)")
        submitted = st.form_submit_button("Submit Request")
    if submitted:
        if not name.strip():
            st.error("Please enter your name.")
            return
        save_leave_request(
            user=st.session_state.get("username", "employee"),
            name=name.strip(),
            type_=leave_type,
            days=int(days),
            reason=reason.strip(),
        )
        st.session_state["flash"] = "✅ Your leave request has been submitted successfully!"
        st.rerun()

def export_buttons(df: pd.DataFrame):
    st.subheader("Export")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name=f"leave_requests_{datetime.now().date()}.csv", mime="text/csv")
    xbio = BytesIO()
    with pd.ExcelWriter(xbio, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="requests")
    st.download_button(
        "Download Excel",
        data=xbio.getvalue(),
        file_name=f"leave_requests_{datetime.now().date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

def page_requests():
    # 🔐 hard guard: non-admins blocked even if they reach here
    require_admin()

    st.header("All Leave Requests")
    flash_show()
    logout_box()

    rows = get_all_leave_requests()
    df = pd.DataFrame(rows, columns=["id", "user", "name", "type", "days", "reason", "status", "created_at"])
    export_buttons(df)
    st.subheader("Approve or Reject")

    if df.empty:
        st.info("No requests found.")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)

    for _, r in df.iterrows():
        with st.container():
            st.markdown(
                f"**#{int(r['id'])} — {r['name']} | {r['type']} | {int(r['days'])} day(s) | Status: {r['status']}**"
                f"<br/>Reason: {r['reason'] or '—'} | Created: {r['created_at']}",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([1, 1])
            if c1.button("Approve", key=f"approve_{r['id']}"):
                update_leave_status(int(r["id"]), "Approved")
                st.session_state["flash"] = f"✅ Request {int(r['id'])} approved!"
                st.rerun()
            if c2.button("Reject", key=f"reject_{r['id']}"):
                update_leave_status(int(r["id"]), "Rejected")
                st.session_state["flash"] = f"❌ Request {int(r['id'])} rejected!"
                st.rerun()
            st.divider()

# ---------- router ----------
def main():
    if not st.session_state.get("logged_in"):
        page_login()
        return

    role = st.session_state.get("role")
    st.sidebar.title("Choose a section")

    if role == "admin":
        choice = st.sidebar.radio("", ["Dashboard", "Submit Leave Request", "View Requests"])
    else:
        # Employee NEVER sees "View Requests"
        choice = st.sidebar.radio("", ["Dashboard", "Submit Leave Request"])

    if choice == "Dashboard":
        page_dashboard()
    elif choice == "Submit Leave Request":
        page_submit()
    elif choice == "View Requests":
        page_requests()  # inside it we check require_admin()

if __name__ == "__main__":
    main()
