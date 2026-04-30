"""
PeakForm — Promote a user to Admin role.

Usage:
    python promote_admin.py user@example.com

One-liner alternative (run from d:\\PeakForm):
    python -c "import sqlite3,sys;from backend.services.encryption_service import blind_index;db=sqlite3.connect('database/peakform.db');r=db.execute('UPDATE users SET role=? WHERE email_index=?',('admin',blind_index(sys.argv[1])));db.commit();print(f'Updated {r.rowcount} row(s)')" YOUR_EMAIL@HERE.COM
"""
import sys, os

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.encryption_service import blind_index
import sqlite3

def promote(email: str):
    db_path = os.path.join(os.path.dirname(__file__), "database", "peakform.db")
    conn = sqlite3.connect(db_path)
    idx = blind_index(email.strip().lower())
    cur = conn.execute("UPDATE users SET role = 'admin' WHERE email_index = ?", (idx,))
    conn.commit()
    if cur.rowcount:
        print(f"✅ '{email}' has been promoted to admin. Please log out and back in.")
    else:
        print(f"❌ No user found with email '{email}'. Check the spelling.")
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promote_admin.py user@example.com")
        sys.exit(1)
    promote(sys.argv[1])
