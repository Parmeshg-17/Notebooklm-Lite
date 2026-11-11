import sqlite3

conn = sqlite3.connect('backend/notebooklm.db')
c = conn.cursor()
c.execute("SELECT typeof(id), length(id), id, email, full_name FROM users WHERE email LIKE '%elena%'")
for row in c.fetchall():
    print("User:", row)

