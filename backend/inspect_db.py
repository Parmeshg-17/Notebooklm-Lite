import sqlite3

conn = sqlite3.connect("backend/notebooklm.db")
c = conn.cursor()
c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
for tname, sql in tables:
    print(f"=== {tname} ===")
    print(sql)
    print()

c.execute("SELECT id, title, owner_id FROM notebooks")
print("Notebooks:", c.fetchall())

c.execute("SELECT id, filename, notebook_id, processing_status, page_count FROM documents")
print("Documents:", c.fetchall())
