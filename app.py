
import streamlit as st
from db import (
    get_user_by_credentials, add_leave_request, get_requests_for_user,
    update_request_status, get_summary_counts, get_counts_by_type,
    df_to_csv_bytes, df_to_excel_bytes
)
import pandas as pd
import plotly.express as px
from langdetect import detect, LangDetectException
import os

# compatibility fallback for st.experimental_rerun
if not hasattr(st, "experimental_rerun"):
    def _noop_rerun():
        return None
    st.experimental_rerun = _noop_rerun

st.set_page_config(layout="wide", page_title="HR Query Management", page_icon="🧑‍💼")

# Chatbot fallback
def local_chatbot_reply(msg: str, lang_hint: str = None) -> str:
    try:
        lang = lang_hint or detect(msg)
    except LangDetectException:
        lang = "en"
    replies = {
        "en": "Hello! How can I assist you today?",
        "ta": "வணக்கம்! இன்று உங்களுக்கு நான் எப்படி உதவ முடியும்?",
        "hi": "नमस्ते! मैं आपकी कैसे मदद कर सकता/सकती हूँ?",
        "es": "¡Hola! ¿En qué puedo ayudarte?",
        "fr": "Bonjour! Comment puis-je vous aider aujourd'hui?",
        "sw": "Habari! Naweza kukusaidiaje leo?",
    }
    return replies.get(lang, replies["en"])

OPENAI_AVAILABLE = False
try:
    import openai
    key = None
    if "OPENAI_API_KEY" in st.secrets:
        key = st.secrets["OPENAI_API_KEY"]
    elif os.environ.get("OPENAI_API_KEY"):
        key = os.environ.get("OPENAI_API_KEY")
    if key:
        openai.api_key = key
        OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

def call_openai_reply(msg):
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content": msg}],
            max_tokens=120
        )
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(OpenAI error) {e}"

# Auth
def show_login():
    st.title("Login")
    st.info("Default: admin/admin or emp123/emp123. Thunderland user: thunderland/Thund3r!and")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        user = get_user_by_credentials(username.strip(), password.strip())
        if user:
            st.session_state["user"] = user
            st.success(f"Logged in as: {user['username']} ({user['role']})")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

def logout():
    if "user" in st.session_state:
        del st.session_state["user"]
    st.experimental_rerun()

# Pages
def dashboard_page():
    st.header("Overview")
    stats = get_summary_counts()
    col1, col2, col3, col4 = st.columns([1,1,1,2])
    col1.metric("Total requests", stats["total"])
    col2.metric("Approved", stats["approved"])
    col3.metric("Pending", stats["pending"])
    col4.metric("Rejected", stats["rejected"])

    rows = get_counts_by_type()
    df = pd.DataFrame(rows, columns=["type", "count"])
    if df.empty:
        st.info("No data to chart yet.")
    else:
        fig = px.bar(df, x="type", y="count", title="Requests by Type")
        st.plotly_chart(fig, use_container_width=True)
        fig2 = px.pie(df, names="type", values="count", title="Requests distribution")
        st.plotly_chart(fig2, use_container_width=True)

def submit_request_page(current_user):
    st.header("Submit leave request")
    with st.form("leave_form", clear_on_submit=False):
        name = st.text_input("Your Name", value=current_user.get("name", ""))
        leave_type = st.selectbox("Select leave type", ["Casual Leave", "Sick Leave", "Other"])
        days = st.number_input("Number of days", min_value=1, value=1)
        reason = st.text_area("Reason (optional)")
        submitted = st.form_submit_button("Submit")
    if submitted:
        add_leave_request(current_user["username"], name, leave_type, int(days), reason)
        st.success("Leave request submitted successfully.")
        st.experimental_rerun()

def view_requests_page(current_user):
    st.header("All Leave Requests")
    is_admin = current_user["role"] == "admin"

    with st.expander("Filters", expanded=True):
        q = st.text_input("Search (name, reason, type)")
        status = st.selectbox("Status", ["All", "Pending", "Approved", "Rejected"])
        rtype = st.selectbox("Type", ["All", "Casual Leave", "Sick Leave", "Other"])
        c1, c2 = st.columns(2)
        date_from = c1.date_input("From", value=None)
        date_to = c2.date_input("To", value=None)
        st.button("Apply filters")  # triggers rerun if user expects

    filters = {}
    if q:
        filters["q"] = q
    if status and status != "All":
        filters["status"] = status
    if rtype and rtype != "All":
        filters["type"] = rtype
    if date_from:
        filters["date_from"] = date_from.isoformat()
    if date_to:
        filters["date_to"] = date_to.isoformat()

    df = get_requests_for_user(username=(None if is_admin else current_user["username"]),
                               only_admin=is_admin, filters=filters)
    st.write(f"Found {len(df)} rows")
    if not df.empty:
        st.dataframe(df)
        csv_bytes = df_to_csv_bytes(df)
        excel_bytes = df_to_excel_bytes(df)
        col1, col2 = st.columns(2)
        col1.download_button("Download CSV", data=csv_bytes, file_name="leave_requests.csv", mime="text/csv")
        col2.download_button("Download Excel", data=excel_bytes, file_name="leave_requests.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if is_admin:
            st.subheader("Approve or Reject")
            for idx, row in df.iterrows():
                st.write(f"#{row['id']} - {row['name']} ({row['type']}) - Status: {row['status']}")
                c1, c2 = st.columns(2)
                if c1.button(f"Approve #{row['id']}", key=f"appr-{row['id']}"):
                    update_request_status(int(row['id']), "Approved")
                    st.success(f"Request #{row['id']} approved.")
                    st.experimental_rerun()
                if c2.button(f"Reject #{row['id']}", key=f"rej-{row['id']}"):
                    update_request_status(int(row['id']), "Rejected")
                    st.success(f"Request #{row['id']} rejected.")
                    st.experimental_rerun()
    else:
        st.info("No matching requests found.")

def chatbot_page(current_user):
    st.header("Multilingual HR Chatbot")
    st.info("Enter a question and press Send. If OpenAI key is configured, it will call the API; otherwise a local demo reply is used.")
    msg = st.text_input("Enter your message")
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if st.button("Send"):
        if not msg:
            st.warning("Please enter a message.")
        else:
            try:
                lang = detect(msg)
            except Exception:
                lang = None
            if OPENAI_AVAILABLE:
                reply = call_openai_reply(msg)
            else:
                reply = local_chatbot_reply(msg, lang_hint=lang)
            st.session_state["chat_history"].append(("You", msg))
            st.session_state["chat_history"].append(("Bot", reply))
            st.success("Message processed.")

    for speaker, text in st.session_state.get("chat_history", [])[::-1]:
        if speaker == "You":
            st.markdown(f"**You:** {text}")
        else:
            st.markdown(f"**Bot:** {text}")

def main():
    if "user" not in st.session_state:
        show_login()
        return

    user = st.session_state["user"]
    st.sidebar.title("Navigation")
    st.sidebar.write(f"Logged in as: {user['username']} ({user['role']})")
    st.sidebar.button("Logout", on_click=logout)

    pages = ["Dashboard", "Submit Leave Request", "View Requests", "Chatbot"]
    choice = st.sidebar.radio("Choose a section", pages, index=0)

    if choice == "Dashboard":
        dashboard_page()
    elif choice == "Submit Leave Request":
        submit_request_page(user)
    elif choice == "View Requests":
        view_requests_page(user)
    elif choice == "Chatbot":
        chatbot_page(user)

if __name__ == "__main__":
    main()
