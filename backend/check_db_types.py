import sqlite3

conn = sqlite3.connect('backend/notebooklm.db')
c = conn.cursor()
c.execute("SELECT typeof(id), length(id), id, title, owner_id FROM notebooks WHERE instr(id, '438c') > 0")
for row in c.fetchall():
    print("Notebook:", row)

c.execute("SELECT typeof(id), length(id), id, notebook_id, filename, processing_status FROM documents WHERE instr(notebook_id, '438c') > 0")
for row in c.fetchall():
    print("Document:", row)

