"""
Database layer — automatically uses PostgreSQL on Railway, SQLite locally.
"""
import json, os, sqlite3
from datetime import datetime

_PG_FALLBACK = "postgresql://postgres:ZKpYAzKAeQARWiXJsLsZmmCQuPwOumbS@gondola.proxy.rlwy.net:35819/railway"
DATABASE_URL = os.getenv('DATABASE_URL') or _PG_FALLBACK
USE_PG = True  # Always use PostgreSQL


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
    stakeholder_name TEXT,
    visit_reason TEXT, meeting_type TEXT,
    account_manager_present INTEGER, admin_manager_present INTEGER,
    meeting_datetime TEXT, meeting_objective TEXT,
    next_visit_date TEXT, notes TEXT, follow_up_actions TEXT,
    raw_message TEXT,
    checkin_date TEXT, checkin_start_time TEXT, checkin_end_time TEXT,
    checkin_approach TEXT, associated_mpr INTEGER, objectives_list TEXT,
    cs_dir_attended INTEGER, mpm_attended INTEGER, hesham_attended INTEGER,
    renewal_acct_mgr_attended INTEGER, sentiment TEXT,
    mom_generated INTEGER, mom_shared INTEGER, feedback_shared INTEGER,
    created_at TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    synced INTEGER DEFAULT 0
);
"""

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT, employee_name TEXT,
    client_name TEXT, account_number TEXT, product TEXT,
    stakeholder_name TEXT,
    visit_reason TEXT, meeting_type TEXT,
    account_manager_present INTEGER, admin_manager_present INTEGER,
    meeting_datetime TEXT, meeting_objective TEXT,
    next_visit_date TEXT, notes TEXT, follow_up_actions TEXT,
    raw_message TEXT, 
    checkin_date TEXT, checkin_start_time TEXT, checkin_end_time TEXT,
    checkin_approach TEXT, associated_mpr INTEGER, objectives_list TEXT,
    cs_dir_attended INTEGER, mpm_attended INTEGER, hesham_attended INTEGER,
    renewal_acct_mgr_attended INTEGER, sentiment TEXT,
    mom_generated INTEGER, mom_shared INTEGER, feedback_shared INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
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
    """Convert Python bool to the right type for the active DB.
    PostgreSQL has native BOOLEAN columns → keep True/False.
    SQLite stores booleans as INTEGER → convert to 1/0.
    """
    if v is True:
        return True if USE_PG else 1
    if v is False:
        return False if USE_PG else 0
    # Handles string 'true'/'false' coming from the frontend radio buttons
    if isinstance(v, str):
        if v.lower() == 'true':
            return True if USE_PG else 1
        if v.lower() == 'false':
            return False if USE_PG else 0
    return None

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
    objectives = json.dumps(data.get('objectives_list') or [], ensure_ascii=False)
    
    fields = {
        'employee_id': emp_id,
        'employee_name': emp_name,
        'client_name': data.get('client_name'),
        'account_number': data.get('account_number'),
        'product': data.get('product'),
        'visit_reason': data.get('visit_reason'),
        'meeting_type': data.get('meeting_type'),
        'account_manager_present': b(data.get('account_manager_present')),
        'admin_manager_present': b(data.get('admin_manager_present')),
        'meeting_datetime': data.get('meeting_datetime'),
        'meeting_objective': data.get('meeting_objective'),
        'next_visit_date': data.get('next_visit_date'),
        'notes': data.get('notes'),
        'follow_up_actions': actions,
        'raw_message': raw,
        'stakeholder_name': data.get('stakeholder_name'),
        # New columns 
        'checkin_date': data.get('checkin_date'),
        'checkin_start_time': data.get('checkin_start_time'),
        'checkin_end_time': data.get('checkin_end_time'),
        'checkin_approach': data.get('checkin_approach'),
        'associated_mpr': b(data.get('associated_mpr')),
        'objectives_list': objectives,
        'cs_dir_attended': b(data.get('cs_dir_attended')),
        'mpm_attended': b(data.get('mpm_attended')),
        'hesham_attended': b(data.get('hesham_attended')),
        'renewal_acct_mgr_attended': b(data.get('renewal_acct_mgr_attended')),
        'sentiment': data.get('sentiment'),
        'mom_generated': b(data.get('mom_generated')),
        'mom_shared': b(data.get('mom_shared')),
        'feedback_shared': b(data.get('feedback_shared')),
    }
    
    cols = list(fields.keys())
    vals = tuple(fields[col] for col in cols)
    placeholders = ','.join(['%s'] * len(cols))
    col_names = ','.join(cols)
    
    SQL = f"INSERT INTO checkins ({col_names}) VALUES({placeholders})"

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

# ── Fetch latest ──────────────────────────────────────────────────────────────
def get_latest_checkin(emp_id, client_name, stakeholder_name=None):
    initialize_db()
    
    # We remove employee_id=%s so it pulls the latest visit for this client COMPANY-WIDE!
    if USE_PG:
        SQL = "SELECT * FROM checkins WHERE client_name ILIKE %s"
        vals = [f"%{client_name}%"]
    else:
        SQL = "SELECT * FROM checkins WHERE client_name LIKE ?"
        vals = [f"%{client_name}%"]
    
    if stakeholder_name:
        if USE_PG:
            SQL += " AND stakeholder_name ILIKE %s"
            vals.append(f"%{stakeholder_name}%")
        else:
            SQL += " AND stakeholder_name LIKE ?"
            vals.append(f"%{stakeholder_name}%")
        
    SQL += ' ORDER BY created_at DESC LIMIT 1'
    
    if USE_PG:
        import psycopg2.extras
        conn = get_pg()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(SQL, tuple(vals))
                row = cur.fetchone()
            return row_to_dict(row) if row else None
        finally:
            conn.close()
    else:
        with get_sqlite() as c:
            row = c.execute(SQL.replace('%s','?'), tuple(vals)).fetchone()
        return row_to_dict(row) if row else None

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
def delete_checkin(record_id, employee_id=None, role='employee', employee_name=None):
    initialize_db()
    if role == 'admin':
        SQL = 'DELETE FROM checkins WHERE id=%s'
        args = (record_id,)
    else:
        # Match by ID or Name to handle potential data inconsistencies
        SQL = 'DELETE FROM checkins WHERE id=%s AND (employee_id=%s OR employee_name=%s)'
        args = (record_id, employee_id, employee_name)
    
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

def delete_employee_visits(emp_id):
    """Delete all visits of one employee."""
    initialize_db()
    SQL = 'DELETE FROM checkins WHERE employee_id=%s'
    if USE_PG:
        conn = get_pg()
        try:
            with conn.cursor() as cur: cur.execute(SQL, (emp_id,)); count = cur.rowcount
            conn.commit(); return count
        finally: conn.close()
    else:
        with get_sqlite() as c:
            count = c.execute(SQL.replace('%s','?'), (emp_id,)).rowcount; c.commit(); return count

def delete_all_visits():
    """Delete every visit record."""
    initialize_db()
    if USE_PG:
        conn = get_pg()
        try:
            with conn.cursor() as cur: cur.execute('DELETE FROM checkins'); count = cur.rowcount
            conn.commit(); return count
        finally: conn.close()
    else:
        with get_sqlite() as c:
            count = c.execute('DELETE FROM checkins').rowcount; c.commit(); return count

# ── API for Clients & Stakeholders ────────────────────────────────────────────
def get_clients():
    initialize_db()
    SQL = 'SELECT farabi_account, client_name, acronym, cs_owner, account_manager FROM clients ORDER BY client_name'
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
            try:
                return [dict(r) for r in c.execute(SQL).fetchall()]
            except:
                return []

def get_stakeholders(farabi_account):
    initialize_db()
    SQL = 'SELECT id, stakeholder_name, stakeholder_title, email, mobile_number, influence_level FROM stakeholders WHERE farabi_account=%s ORDER BY stakeholder_name'
    if USE_PG:
        import psycopg2.extras
        conn = get_pg()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(SQL, (farabi_account,))
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    else:
        with get_sqlite() as c:
            try:
                return [dict(r) for r in c.execute(SQL.replace('%s','?'), (farabi_account,)).fetchall()]
            except:
                return []
