import sqlite3
conn = sqlite3.connect('data/betting_bot.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)
if 'predictions' in tables or 'prediction' in tables:
    tbl = 'predictions' if 'predictions' in tables else 'prediction'
    c.execute(f"SELECT sql FROM sqlite_master WHERE name='{tbl}'")
    print(f"Schema for {tbl}:", c.fetchone())
    c.execute(f"SELECT id, home_expected_goals, away_expected_goals, explanation FROM {tbl} LIMIT 5")
    for row in c.fetchall():
        print(row)
else:
    # search for any table with prediction-like name
    print("No predictions table. Looking for similar...")
    for t in tables:
        if 'predict' in t.lower():
            print(f"Found: {t}")
            c.execute(f"SELECT * FROM {t} LIMIT 2")
            print(c.fetchall())
conn.close()
