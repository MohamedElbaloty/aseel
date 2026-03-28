import sqlite3, json, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'checkins.db')

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    with get_conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT, employee_name TEXT,
            client_name TEXT, account_number TEXT, product TEXT,
            visit_reason TEXT, meeting_type TEXT,
            account_manager_present INTEGER, admin_manager_present INTEGER,
            meeting_datetime TEXT, meeting_objective TEXT,
            next_visit_date TEXT, notes TEXT, follow_up_actions TEXT,
            raw_message TEXT, created_at TEXT DEFAULT (datetime('now')),
            synced INTEGER DEFAULT 0
        )''')
        c.commit()

def save_checkin(data, emp_id, emp_name, raw=''):
    initialize_db()
    actions = data.get('follow_up_actions') or []
    def b(v): return 1 if v is True else (0 if v is False else None)
    with get_conn() as c:
        cur = c.execute('''INSERT INTO checkins
            (employee_id,employee_name,client_name,account_number,product,
             visit_reason,meeting_type,account_manager_present,admin_manager_present,
             meeting_datetime,meeting_objective,next_visit_date,notes,
             follow_up_actions,raw_message)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (emp_id, emp_name,
             data.get('client_name'), data.get('account_number'), data.get('product'),
             data.get('visit_reason'), data.get('meeting_type'),
             b(data.get('account_manager_present')), b(data.get('admin_manager_present')),
             data.get('meeting_datetime'), data.get('meeting_objective'),
             data.get('next_visit_date'), data.get('notes'),
             json.dumps(actions, ensure_ascii=False), raw))
        c.commit()
        return cur.lastrowid

def _row(r):
    d = dict(r)
    try: d['follow_up_actions'] = json.loads(d.get('follow_up_actions') or '[]')
    except: d['follow_up_actions'] = []
    return d

def get_all_checkins(limit=200):
    initialize_db()
    with get_conn() as c:
        rows = c.execute('SELECT * FROM checkins ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
    return [_row(r) for r in rows]

def get_employee_checkins(emp_id, limit=10):
    initialize_db()
    with get_conn() as c:
        rows = c.execute('SELECT * FROM checkins WHERE employee_id=? ORDER BY created_at DESC LIMIT ?', (emp_id, limit)).fetchall()
    return [_row(r) for r in rows]

def get_stats():
    initialize_db()
    today = datetime.now().strftime('%Y-%m-%d')
    with get_conn() as c:
        total = c.execute('SELECT COUNT(*) FROM checkins').fetchone()[0]
        today_c = c.execute("SELECT COUNT(*) FROM checkins WHERE created_at LIKE ?", (f'{today}%',)).fetchone()[0]
        emps = c.execute('SELECT COUNT(DISTINCT employee_id) FROM checkins').fetchone()[0]
        in_person = c.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='in_person'").fetchone()[0]
        phone = c.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='phone_call'").fetchone()[0]
        online = c.execute("SELECT COUNT(*) FROM checkins WHERE meeting_type='online'").fetchone()[0]
        weekly = c.execute("SELECT COUNT(*) FROM checkins WHERE created_at >= date('now','-7 days')").fetchone()[0]
        monthly = c.execute("SELECT COUNT(*) FROM checkins WHERE created_at >= date('now','-30 days')").fetchone()[0]
    return {'total': total, 'today': today_c, 'employees': emps,
            'weekly': weekly, 'monthly': monthly,
            'by_type': {'in_person': in_person, 'phone_call': phone, 'online': online}}

def get_employees():
    initialize_db()
    with get_conn() as c:
        rows = c.execute('SELECT DISTINCT employee_id, employee_name FROM checkins ORDER BY employee_name').fetchall()
    return [dict(r) for r in rows]

def delete_checkin(record_id, employee_id=None, role='employee'):
    """Delete a check-in. Employees can only delete their own. Admins delete any."""
    initialize_db()
    with get_conn() as c:
        if role == 'admin':
            affected = c.execute('DELETE FROM checkins WHERE id=?', (record_id,)).rowcount
        else:
            affected = c.execute('DELETE FROM checkins WHERE id=? AND employee_id=?', (record_id, employee_id)).rowcount
        c.commit()
    return affected > 0

