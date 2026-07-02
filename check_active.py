import sqlite3
conn = sqlite3.connect('data/betting_bot.db')
cur = conn.execute('SELECT id, model_name, target_variable, is_active FROM model_registry WHERE is_active = 1')
for r in cur.fetchall():
    print(f"Active: id={r[0]} name={r[1]} target={r[2]} active={r[3]}")
conn.close()
