"""
Seed script — reads REAL clients from the DB and inserts realistic
chekc-in visits for every employee.  Uses a single persistent PG
connection so there are no reconnection timeouts.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2, psycopg2.extras
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

_PG_FALLBACK = "postgresql://postgres:ZKpYAzKAeQARWiXJsLsZmmCQuPwOumbS@gondola.proxy.rlwy.net:35819/railway"
DATABASE_URL = os.getenv('DATABASE_URL') or _PG_FALLBACK

USERS = {
    "emp001": {"name": "أحمد المنصوري"},
    "emp002": {"name": "سارة الزهراني"},
    "emp003": {"name": "خالد العمري"},
}

print("Connecting to PostgreSQL …")
conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
conn.autocommit = False
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── Read real clients + stakeholders ─────────────────────────────────────────
cur.execute("""
    SELECT c.client_name, c.farabi_account, s.stakeholder_name, s.stakeholder_title
    FROM   clients c
    JOIN   stakeholders s ON c.farabi_account = s.farabi_account
    ORDER  BY random()
    LIMIT  5
""")
rows = cur.fetchall()
print(f"Got {len(rows)} real client/stakeholder combos:")
for r in rows:
    print(f"  • {r['client_name']} ({r['farabi_account']}) — {r['stakeholder_name']}")

# ── Delete old fake/seed records ─────────────────────────────────────────────
cur.execute("""
    DELETE FROM checkins
    WHERE client_name IN ('maaden','Mobily','stc')
""")
deleted = cur.rowcount
conn.commit()
print(f"\nDeleted {deleted} old fake records.")

# ── Build visits list from real data ─────────────────────────────────────────
products   = ["RiCH", "Availo", "OLE5", "Msegat"]
approaches = ["Proactive Check-In", "Reactive Check-In"]
types      = ["On-Site Visit", "On-Line Meeting", "Phone Call"]
sentiments = ["Positive", "Neutral", "Negative"]
obj_pool   = [
    "Kick-Off Meeting", "Drive Feature/Service Adoption",
    "Feedback Collection", "Stakeholder Relationship Management",
    "Product Update Announcement", "New Need Discussion"
]

import random
random.seed(42)

def make_visit(row, idx):
    objs = random.sample(obj_pool, k=2)
    return {
        "client_name":               row["client_name"],
        "account_number":            row["farabi_account"],
        "product":                   random.choice(products),
        "stakeholder_name":          row["stakeholder_name"],
        "checkin_approach":          random.choice(approaches),
        "meeting_type":              random.choice(types),
        "associated_mpr":            random.choice([True, False]),
        "objectives_list":           objs,
        "meeting_objective":         f"Discussing {objs[0]} with {row['stakeholder_name']}.",
        "cs_dir_attended":           random.choice([True, False]),
        "mpm_attended":              random.choice([True, False]),
        "hesham_attended":           random.choice([True, False]),
        "renewal_acct_mgr_attended": random.choice([True, False]),
        "sentiment":                 random.choice(sentiments),
        "mom_generated":             True,
        "mom_shared":                random.choice([True, False]),
        "feedback_shared":           random.choice([True, False]),
        "notes":                     f"Visit notes for {row['client_name']} — session {idx+1}.",
        "follow_up_actions":         ["Follow up on action items", "Share MoM"],
        "checkin_date":              f"2026-03-{20+idx:02d}",
        "checkin_start_time":        f"{9+idx:02d}:00",
        "checkin_end_time":          f"{10+idx:02d}:30",
        "next_visit_date":           f"2026-04-{5+idx:02d}",
    }

visits = [make_visit(rows[i % len(rows)], i) for i in range(len(rows))]

# ── Insert for every employee ─────────────────────────────────────────────────
insert_cols = [
    "employee_id","employee_name","client_name","account_number","product",
    "stakeholder_name","checkin_approach","meeting_type","associated_mpr",
    "objectives_list","meeting_objective","cs_dir_attended","mpm_attended",
    "hesham_attended","renewal_acct_mgr_attended","sentiment",
    "mom_generated","mom_shared","feedback_shared","notes","follow_up_actions",
    "checkin_date","checkin_start_time","checkin_end_time","next_visit_date",
]

plain_cur = conn.cursor()   # plain cursor for INSERT
total = 0
for uid, udata in USERS.items():
    print(f"\nInserting for {uid} — {udata['name']}")
    for v in visits:
        vals = (
            uid, udata["name"],
            v["client_name"], v["account_number"], v["product"],
            v["stakeholder_name"], v["checkin_approach"], v["meeting_type"],
            v["associated_mpr"],
            json.dumps(v["objectives_list"], ensure_ascii=False),
            v["meeting_objective"],
            v["cs_dir_attended"], v["mpm_attended"],
            v["hesham_attended"], v["renewal_acct_mgr_attended"],
            v["sentiment"],
            v["mom_generated"], v["mom_shared"], v["feedback_shared"],
            v["notes"],
            json.dumps(v["follow_up_actions"], ensure_ascii=False),
            v["checkin_date"], v["checkin_start_time"], v["checkin_end_time"],
            v["next_visit_date"],
        )
        placeholders = ",".join(["%s"] * len(insert_cols))
        SQL = f"INSERT INTO checkins ({','.join(insert_cols)}) VALUES ({placeholders})"
        try:
            plain_cur.execute(SQL, vals)
            print(f"  ✓ {v['client_name']}")
            total += 1
        except Exception as e:
            conn.rollback()
            print(f"  ✗ ERROR: {e}")

conn.commit()
conn.close()
print(f"\n✅ Done! Inserted {total} visits total.")
