
import sqlite3
from datetime import datetime
from pathlib import Path

DB_FILE = "hr_system.db"

# -------------------------
# DB helpers
# -------------------------
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

def ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    # users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)
    # leave requests table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        leave_type TEXT,
        days INTEGER,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

# Insert default accounts (admin + employee)
def insert_default_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", "password123", "admin"))
    cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                ("employee", "emp123", "employee"))
    conn.commit()
    conn.close()

# -------------------------
# DB operations used by app
# -------------------------
def login_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "role": row[2]}
    return None

def save_leave_request(name, leave_type, days, reason=""):
    conn = get_conn()
    cur = conn.cursor()
    created_at = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO leave_requests (name, leave_type, days, reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, leave_type, days, reason, "Pending", created_at))
    conn.commit()
    conn.close()

def get_all_leave_requests():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, leave_type, days, reason, status, created_at FROM leave_requests ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_leave_status(request_id, new_status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE leave_requests SET status=? WHERE id=?", (new_status, request_id))
    conn.commit()
    conn.close()

# Ensure DB exists with tables and default users when this module is first imported
if not Path(DB_FILE).exists():
    ensure_tables()
    insert_default_users()
else:
    # in case DB exists but tables not created
    ensure_tables()
    insert_default_users()