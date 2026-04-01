import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'db.sqlite3')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courses_answer';")
    print(cur.fetchone())
    conn.close()
