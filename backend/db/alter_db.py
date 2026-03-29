import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import get_pg

def alter():
    conn = get_pg()
    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE checkins ADD COLUMN stakeholder_name TEXT;")
        conn.commit()
        print("Column added")
    except Exception as e:
        print("Failed to add column", e)
    finally:
        conn.close()

if __name__ == '__main__':
    alter()
