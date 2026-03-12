import sqlite3
DB_FILE = "hr_app.db"

schema = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    name TEXT,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT NOT NULL,
    name TEXT,
    type TEXT,
    days INTEGER,
    reason TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT,
    FOREIGN KEY(user) REFERENCES users(username)
);
"""

seed_users = [
    ("admin", "admin", "Admin User", "admin"),
    ("emp123", "emp123", "Employee One", "employee"),
    # remove or modify other demo users if you don't want them
    # ("thunderland", "Thund3r!and", "Thunder", "admin"),
]

def reset_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.executescript(schema)
    # seed users if not exists
    for u in seed_users:
        c.execute("INSERT OR IGNORE INTO users (username,password,name,role) VALUES (?,?,?,?)", u)
    conn.commit()
    conn.close()
    print("DB created/updated:", DB_FILE)

if __name__ == "__main__":
    reset_db()
