
import streamlit as st
from datetime import datetime
from db import login_user, save_leave_request, get_all_leave_requests, update_leave_status

st.set_page_config(page_title="HR Assistant", layout="wide")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

def login_flow():
    st.title("HR AI Assistant — Login")
    st.info("Default accounts: admin/password123  |  employee/emp123")
    username = st.text_input("Enter username")
    password = st.text_input("Enter password", type="password")
    if st.button("Login"):
        user = login_user(username.strip(), password.strip())
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.success(f"Logged in as {user['username']} ({user['role']})")
        else:
            st.error("Invalid Username or Password")

def employee_dashboard():
    st.header("Leave Request Form")
    name = st.text_input("Enter your name", value=st.session_state.user["username"])
    leave_type = st.selectbox("Select Leave Type", ["Casual Leave", "Sick Leave", "Earned Leave", "Work From Home"])
    days = st.number_input("Number of days", min_value=1, step=1, value=1)
    reason = st.text_area("Reason (optional)")
    if st.button("Submit Request"):
        save_leave_request(name, leave_type, int(days), reason)
        st.success(f"Leave request submitted for {name} — {days} day(s) of {leave_type}")

    st.markdown("---")
    st.subheader("My Requests")
    all_requests = get_all_leave_requests()
    # filter by username
    my = [r for r in all_requests if r[1] == st.session_state.user["username"]]
    if not my:
        st.info("No leave requests found for you.")
    else:
        for r in my:
            rid, rname, rtype, rdays, rreason, rstatus, rcreated = r
            st.write(f"**{rname}** | {rtype} | {rdays} days | Status: **{rstatus}**")
            if rreason:
                st.write(f"> Reason: {rreason}")
            st.write(f"_Created at:_ {rcreated}")
            st.markdown("---")

def admin_dashboard():
    st.header("All Leave Requests")
    requests = get_all_leave_requests()
    if not requests:
        st.info("No leave requests yet.")
        return
    # Table view as interactive rows
    for r in requests:
        rid, rname, rtype, rdays, rreason, rstatus, rcreated = r
        cols = st.columns([2,2,1,1,2,1])
        cols[0].write(f"**{rname}**")
        cols[1].write(f"{rtype}")
        cols[2].write(f"{rdays}")
        cols[3].write(f"{rstatus}")
        cols[4].write(f"_Created:_ {rcreated}")
        with cols[5]:
            if rstatus != "Approved":
                if st.button(f"Approve {rid}", key=f"ap_{rid}"):
                    update_leave_status(rid, "Approved")
                    st.success(f"Request {rid} approved.")
            if rstatus != "Rejected":
                if st.button(f"Reject {rid}", key=f"rej_{rid}"):
                    update_leave_status(rid, "Rejected")
                    st.info(f"Request {rid} rejected.")
        if rreason:
            st.write(f"> Reason: {rreason}")
        st.markdown("---")

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.experimental_rerun()

# Main UI
if not st.session_state.logged_in:
    login_flow()
else:
    user = st.session_state.user
    st.sidebar.success(f"Logged in as {user['username']} ({user['role']})")
    if st.sidebar.button("Logout"):
        # simple logout
        st.session_state.logged_in = False
        st.session_state.user = None
        st.experimental_rerun()

    choice = st.sidebar.radio("Choose a section", ["Dashboard", "View Requests", "Chatbot"])
    if choice == "Dashboard":
        if user["role"] == "admin":
            admin_dashboard()
        else:
            employee_dashboard()
    elif choice == "View Requests":
        # show same as admin for admin, or show user's requests otherwise
        if user["role"] == "admin":
            admin_dashboard()
        else:
            employee_dashboard()
    else:
        st.header("HR Chatbot (placeholder)")
        st.write("LLM integration coming soon. Right now the chatbot is a placeholder. Once integrated it will answer HR queries like salary status, leave balance, policies, etc.")