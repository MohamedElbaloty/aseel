import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import get_pg

columns_to_add = [
    ("checkin_date", "TEXT"),
    ("checkin_start_time", "TEXT"),
    ("checkin_end_time", "TEXT"),
    ("checkin_approach", "TEXT"),
    ("associated_mpr", "BOOLEAN"),
    ("objectives_list", "TEXT"),
    ("cs_dir_attended", "BOOLEAN"),
    ("mpm_attended", "BOOLEAN"),
    ("hesham_attended", "BOOLEAN"),
    ("renewal_acct_mgr_attended", "BOOLEAN"),
    ("sentiment", "TEXT"),
    ("mom_generated", "BOOLEAN"),
    ("mom_shared", "BOOLEAN"),
    ("feedback_shared", "BOOLEAN")
]

def alter():
    conn = get_pg()
    for col_name, col_type in columns_to_add:
        try:
            with conn.cursor() as cur:
                cur.execute(f"ALTER TABLE checkins ADD COLUMN {col_name} {col_type};")
            conn.commit()
            print(f"Added {col_name}")
        except Exception as e:
            print(f"Skipped {col_name} (might already exist)")
            conn.rollback()
    
    conn.close()

if __name__ == '__main__':
    alter()
