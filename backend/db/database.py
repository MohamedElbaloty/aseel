"""
Database layer — automatically uses PostgreSQL on Railway, SQLite locally.
"""
import json, os, sqlite3
from datetime import datetime

DATABASE_URL = os.getenv('DATABASE_URL')  # Set by Railway when PostgreSQL is added
USE_PG = bool(DATABASE_URL)

# ── PostgreSQL helpers ────────────────────────────────────────────────────────
def get_pg():
    import psycopg2, psycopg2.extras
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn

# ── SQLite helpers ────────────────────────────────────────────────────────────
SQLITE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'checkins.db')

def get_sqlite():
    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Schema ────────────────────────────────────────────────────────────────────
PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkins (
    id SERIAL PRIMARY KEY,
    employee_id TEXT, employee_name TEXT,
    client_name TEXT, account_number TEXT, product TEXT,
    visit_reason TEXT, meeting_type TEXT,
    account_manager_present INTEGER, admin_manager_present INTEGER,
    meeting_datetime TEXT, meeting_objective TEXT,
    next_visit_date TEXT, notes TEXT, follow_up_actions TEXT,
    raw_message TEXT,
    created_at TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    synced INTEGER DEFAULT 0
);
"""

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT, employee_name TEXT,
    client_name TEXT, account_number TEXT, product TEXT,
    visit_reason TEXT, meeting_type TEXT,
    account_manager_present INTEGER, admin_manager_present INTEGER,
    meeting_datetime TEXT, meeting_objective TEXT,
    next_visit_date TEXT, notes TEXT, follow_up_actions TEXT,
    raw_message TEXT, created_at TEXT DEFAULT (datetime('now')),
    synced INTEGER DEFAULT 0
);
"""

def initialize_db():
    if USE_PG:
        conn = get_pg()
        try:
            with conn.cursor() as cur:
                cur.execute(PG_SCHEMA)
            conn.commit()
        finally:
            conn.close()
    else:
        with get_sqlite() as c:
            c.execute(SQLITE_SCHEMA)
            c.commit()

# ── Helpers ───────────────────────────────────────────────────────────────────
def b(v):
    return 1 if v is True else (0 if v is False else None)

def row_to_dict(r):
    if isinstance(r, dict):
        d = r
    else:
        d = dict(r)
    # Parse follow_up_actions if it's a string
    fa = d.get('follow_up_actions')
    if isinstance(fa, str):
        try: d['follow_up_actions'] = json.loads(fa)
        except: d['follow_up_actions'] = []
    elif fa is None:
        d['follow_up_actions'] = []
    return d

# ── Save ──────────────────────────────────────────────────────────────────────
def save_checkin(data, emp_id, emp_name, raw=''):
    initialize_db()
    actions = json.dumps(data.get('follow_up_actions') or [], ensure_ascii=False)
    vals = (
        emp_id, emp_name,
        data.get('client_name'), data.get('account_number'), data.get('product'),
        data.get('visit_reason'), data.get('meeting_type'),
        b(data.get('account_manager_present')), b(data.get('admin_manager_present')),
        data.get('meeting_datetime'), data.get('meeting_objective'),
        data.get('next_visit_date'), data.get('notes'),
        actions, raw
    )
    SQL = """INSERT INTO checkins
        (employee_id,employee_name,client_name,account_number,product,
         visit_reason,meeting_type,account_manager_present,admin_manager_present,
         meeting_datetime,meeting_objective,next_visit_date,notes,
         follow_up_actions,raw_message)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

    if USE_PG:
        conn = get_pg()
        try:
            with conn.cursor() as cur:
                cur.execute(SQL + " RETURNING id", vals)
                record_id = cur.fetchone()[0]
            conn.commit()
            return record_id
        finally:
            conn.close()
    else:
        SQL_LITE = SQL.replace('%s', '?')
        with get_sqlite() as c:
            cur = c.execute(SQL_LITE, vals)
            c.commit()
            return cur.lastrowid

# ── Fetch all ─────────────────────────────────────────────────────────────────
def get_all_checkins(limit=200):
    initialize_db()
    SQL = 'SELECT * FROM checkins ORDER BY created_at DESC LIMIT %s'
    if USE_PG:
        import psycopg2.extras
        conn = get_pg()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(SQL, (limit,))
                rows = cur.fetchall()
            return [row_to_dict(r) for r in rows]
        finally:
            conn.close()
    else:
        with get_sqlite() as c:
            rows = c.execute(SQL.replace('%s','?'), (limit,)).fetchall()
        return [row_to_dict(r) for r in rows]

# ── Fetch employee ────────────────────────────────────────────────────────────
def get_employee_checkins(emp_id, limit=20):
    initialize_db()
    SQL = 'SELECT * FROM checkins WHERE employee_id=%s ORDER BY created_at DESC LIMIT %s'
    if USE_PG:
        import psycopg2.extras
        conn = get_pg()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(SQL, (emp_id, limit))
                rows = cur.fetchall()
            return [row_to_dict(r) for r in rows]
        finally:
            conn.close()
    else:
        with get_sqlite() as c:
            rows = c.execute(SQL.replace('%s','?'), (emp_id, limit)).fetchall()
        return [row_to_dict(r) for r in rows]

# ── Stats ─────────────────────────────────────────────────────────────────────
def get_stats():
    initialize_db()
    today = datetime.now().strftime('%Y-%m-%d')
    if USE_PG:
        conn = get_pg()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM checkins'); total = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM checkins WHERE created_at LIKE %s", (f'{today}%',)); today_c = cur.fetchone()[0]
                cur.execute('SELECT COUNT(DISTINCT employee_id) FROM checkins'); emps = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='in_person'"); in_person = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='phone_call'"); phone = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='online'"); online = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM checkins WHERE created_at >= (NOW() - INTERVAL '7 days')::TEXT"); weekly = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM checkins WHERE created_at >= (NOW() - INTERVAL '30 days')::TEXT"); monthly = cur.fetchone()[0]
        finally:
            conn.close()
    else:
        with get_sqlite() as c:
            total     = c.execute('SELECT COUNT(*) FROM checkins').fetchone()[0]
            today_c   = c.execute("SELECT COUNT(*) FROM checkins WHERE created_at LIKE ?", (f'{today}%',)).fetchone()[0]
            emps      = c.execute('SELECT COUNT(DISTINCT employee_id) FROM checkins').fetchone()[0]
            in_person = c.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='in_person'").fetchone()[0]
            phone     = c.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='phone_call'").fetchone()[0]
            online    = c.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='online'").fetchone()[0]
            weekly    = c.execute("SELECT COUNT(*) FROM checkins WHERE created_at >= date('now','-7 days')").fetchone()[0]
            monthly   = c.execute("SELECT COUNT(*) FROM checkins WHERE created_at >= date('now','-30 days')").fetchone()[0]

    return {'total': total, 'today': today_c, 'employees': emps,
            'weekly': weekly, 'monthly': monthly,
            'by_type': {'in_person': in_person, 'phone_call': phone, 'online': online}}

# ── Employees list ────────────────────────────────────────────────────────────
def get_employees():
    initialize_db()
    SQL = 'SELECT DISTINCT employee_id, employee_name FROM checkins ORDER BY employee_name'
    if USE_PG:
        import psycopg2.extras
        conn = get_pg()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(SQL)
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    else:
        with get_sqlite() as c:
            return [dict(r) for r in c.execute(SQL).fetchall()]

# ── Delete ────────────────────────────────────────────────────────────────────
def delete_checkin(record_id, employee_id=None, role='employee'):
    initialize_db()
    if role == 'admin':
        SQL = 'DELETE FROM checkins WHERE id=%s'
        args = (record_id,)
    else:
        SQL = 'DELETE FROM checkins WHERE id=%s AND employee_id=%s'
        args = (record_id, employee_id)

    if USE_PG:
        conn = get_pg()
        try:
            with conn.cursor() as cur:
                cur.execute(SQL, args)
                affected = cur.rowcount
            conn.commit()
            return affected > 0
        finally:
            conn.close()
    else:
        with get_sqlite() as c:
            affected = c.execute(SQL.replace('%s','?'), args).rowcount
            c.commit()
            return affected > 0
