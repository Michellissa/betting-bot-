import sqlite3
conn = sqlite3.connect('data/betting_bot.db')
cur = conn.execute('''
  SELECT r.id, r.model_name, r.target_variable, m.metric_value, r.is_active
  FROM model_registry r
  LEFT JOIN model_metric m ON m.model_id = r.id AND m.metric_name = 'accuracy' AND m.dataset_type = 'test'
  ORDER BY r.target_variable, m.metric_value DESC
''')
rows = cur.fetchall()
print(f"{'id':>3} {'model_name':<25} {'target':<12} {'acc':>8} {'active':>6}")
print('-' * 60)
for r in rows:
    print(f"{r[0]:>3} {r[1]:<25} {r[2]:<12} {r[3]:>8.4f} {str(r[4]):>6}")
conn.close()
