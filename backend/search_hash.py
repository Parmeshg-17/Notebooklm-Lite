import sqlite3

conn = sqlite3.connect('backend/notebooklm.db')
c = conn.cursor()
for table in ['users', 'notebooks', 'documents', 'conversations', 'messages']:
    c.execute(f"PRAGMA table_info({table})")
    cols = [col[1] for col in c.fetchall()]
    for col in cols:
        try:
            c.execute(f"SELECT rowid, {col} FROM {table} WHERE instr(CAST({col} AS TEXT), 'a549') > 0")
            rows = c.fetchall()
            if rows:
                print(f"Found in {table}.{col}:", rows)
        except Exception as e:
            pass

