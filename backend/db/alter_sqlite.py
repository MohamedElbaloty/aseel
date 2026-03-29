import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'app.db')

columns_to_add = [
    ("stakeholder_name", "TEXT"),
    ("checkin_date", "TEXT"),
    ("checkin_start_time", "TEXT"),
    ("checkin_end_time", "TEXT"),
    ("checkin_approach", "TEXT"),
    ("associated_mpr", "INTEGER"),
    ("objectives_list", "TEXT"),
    ("cs_dir_attended", "INTEGER"),
    ("mpm_attended", "INTEGER"),
    ("hesham_attended", "INTEGER"),
    ("renewal_acct_mgr_attended", "INTEGER"),
    ("sentiment", "TEXT"),
    ("mom_generated", "INTEGER"),
    ("mom_shared", "INTEGER"),
    ("feedback_shared", "INTEGER")
]

conn = sqlite3.connect(db_path)
cur = conn.cursor()
for col_name, col_type in columns_to_add:
    try:
        cur.execute(f"ALTER TABLE checkins ADD COLUMN {col_name} {col_type};")
        print(f"Added {col_name} to SQLite")
    except Exception as e:
        print(f"Skipped {col_name}: {e}")
conn.commit()
conn.close()
