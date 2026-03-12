
import sqlite3
import pandas as pd
from typing import Dict

DB_FILE = "hr_app.db"

def get_conn():
    return sqlite3.connect(DB_FILE)

# --- Users ---
def get_user_by_credentials(username: str, password: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, name, role FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "name": row[1], "role": row[2]}
    return None

def get_user_by_username(username: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, name, role FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "name": row[1], "role": row[2]}
    return None

# --- Leave requests ---
def add_leave_request(user: str, name: str, type_: str, days: int, reason: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO leave_requests
                 (user, name, type, days, reason, status, created_at)
                 VALUES (?, ?, ?, ?, ?, 'Pending', datetime('now'))""",
              (user, name, type_, days, reason))
    conn.commit()
    conn.close()

def get_requests_for_user(username: str = None, only_admin=False, filters: Dict = None):
    """
    If username provided and not admin, return only that user's requests.
    filters: dict with keys: q (text search), type, status, date_from, date_to
    """
    conn = get_conn()
    c = conn.cursor()
    sql = "SELECT id, user, name, type, days, reason, status, created_at FROM leave_requests WHERE 1=1"
    params = []
    if username and not only_admin:
        sql += " AND user = ?"
        params.append(username)
    if filters:
        q = filters.get("q")
        if q:
            sql += " AND (name LIKE ? OR reason LIKE ? OR type LIKE ?)"
            like = f"%{q}%"
            params.extend([like, like, like])
        if filters.get("type"):
            sql += " AND type = ?"
            params.append(filters["type"])
        if filters.get("status"):
            sql += " AND status = ?"
            params.append(filters["status"])
        if filters.get("date_from"):
            sql += " AND date(created_at) >= date(?)"
            params.append(filters["date_from"])
        if filters.get("date_to"):
            sql += " AND date(created_at) <= date(?)"
            params.append(filters["date_to"])
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    df = pd.DataFrame(rows, columns=["id", "user", "name", "type", "days", "reason", "status", "created_at"])
    return df

def update_request_status(request_id: int, status: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (status, request_id))
    conn.commit()
    conn.close()

# --- Dashboard stats ---
def get_summary_counts():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM leave_requests")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Approved'")
    approved = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Rejected'")
    rejected = c.fetchone()[0]
    conn.close()
    return {"total": total, "approved": approved, "pending": pending, "rejected": rejected}

def get_counts_by_type():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT type, COUNT(*) FROM leave_requests GROUP BY type")
    rows = c.fetchall()
    conn.close()
    return rows

# --- Export helpers ---
def df_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")

def df_to_excel_bytes(df):
    import io
    with io.BytesIO() as buffer:
        df.to_excel(buffer, index=False, engine="openpyxl")
        return buffer.getvalue()
