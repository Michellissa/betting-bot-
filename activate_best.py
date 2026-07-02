import sqlite3
conn = sqlite3.connect('data/betting_bot.db')
# deactivate all
conn.execute('UPDATE model_registry SET is_active = 0')
# activate best per target: result=XGBoost(id=2), over_2_5=XGBoost(id=7), btts=RF(id=11)
for mid in [2, 7, 11]:
    conn.execute('UPDATE model_registry SET is_active = 1 WHERE id = ?', (mid,))
conn.commit()
cur = conn.execute('SELECT id, model_name, target_variable, is_active FROM model_registry ORDER BY target_variable')
for r in cur.fetchall():
    print(f"  id={r[0]} {r[1]:<25} {r[2]:<12} active={r[3]}")
conn.close()
