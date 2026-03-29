import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import app, USERS
from db.database import get_pg, save_checkin, initialize_db

initialize_db()
print("Initialized")
conn = get_pg()
cur = conn.cursor()
cur.execute("SELECT c.client_name, c.farabi_account, s.stakeholder_name FROM clients c JOIN stakeholders s ON c.farabi_account = s.farabi_account LIMIT 3")
rows = cur.fetchall()
print("Real items:", rows)

visits_to_insert = [
    {
        "client_name": rows[0][0],
        "account_number": rows[0][1],
        "product": "Ole5",
        "stakeholder_name": rows[0][2],
        "checkin_approach": "Proactive Check-In",
        "meeting_type": "On-Site Visit",
        "associated_mpr": True,
        "objectives_list": ["PoC Delivery", "Kick-Off Meeting"],
        "meeting_objective": "Discussing deployment updates and training.",
        "cs_dir_attended": False,
        "mpm_attended": True,
        "hesham_attended": False,
        "renewal_acct_mgr_attended": True,
        "sentiment": "Positive",
        "mom_generated": True,
        "mom_shared": True,
        "feedback_shared": True,
        "notes": "Very happy with the recent updates.",
        "follow_up_actions": ["Send technical proposal", "Schedule HR meeting"],
        "checkin_date": "2026-03-25",
        "checkin_start_time": "10:00",
        "checkin_end_time": "11:30",
        "next_visit_date": "2026-04-10"
    },
    {
        "client_name": rows[1][0],
        "account_number": rows[1][1],
        "product": "RiCH",
        "stakeholder_name": rows[1][2],
        "checkin_approach": "Reactive Check-In",
        "meeting_type": "Phone Call",
        "associated_mpr": False,
        "objectives_list": ["Feedback Collection", "Renewal Discussion"],
        "meeting_objective": "Quarterly review and feedback.",
        "cs_dir_attended": True,
        "mpm_attended": False,
        "hesham_attended": True,
        "renewal_acct_mgr_attended": False,
        "sentiment": "Neutral",
        "mom_generated": True,
        "mom_shared": False,
        "feedback_shared": True,
        "notes": "Requested some custom reports.",
        "follow_up_actions": ["Check with tech team on custom reports"],
        "checkin_date": "2026-03-28",
        "checkin_start_time": "14:00",
        "checkin_end_time": "14:45",
        "next_visit_date": "2026-04-20"
    },
    {
        "client_name": rows[2][0],
        "account_number": rows[2][1],
        "product": "Msegat",
        "stakeholder_name": rows[2][2],
        "checkin_approach": "Proactive Check-In",
        "meeting_type": "On-Line Meeting",
        "associated_mpr": True,
        "objectives_list": ["Demo / Presentation"],
        "meeting_objective": "Showcasing API integration features.",
        "cs_dir_attended": False,
        "mpm_attended": False,
        "hesham_attended": True,
        "renewal_acct_mgr_attended": False,
        "sentiment": "Positive",
        "mom_generated": True,
        "mom_shared": True,
        "feedback_shared": True,
        "notes": "Very interested in the new features.",
        "follow_up_actions": ["Share API documentation link", "Generate trial credentials"],
        "checkin_date": "2026-03-29",
        "checkin_start_time": "09:00",
        "checkin_end_time": "10:00",
        "next_visit_date": "2026-04-05"
    }
]

# Delete old fake records!
cur.execute("DELETE FROM checkins WHERE client_name IN ('maaden', 'Mobily', 'stc', 'maaden - maaden')")
conn.commit()

with app.app_context():
    for user_id, user_data in USERS.items():
        if user_data.get('role') != 'employee':
            continue
            
        print(f"Injecting visits for user: {user_id} - {user_data['name']}")
        for visit in visits_to_insert:
            try:
                save_checkin(visit, user_id, user_data['name'])
                print(f"   Saved {visit['client_name']}")
            except Exception as e:
                print(f"   Error: {e}")
                
print("Finished Realistic Seeding on Railway DB with REAL CLIENT NAMES!")
