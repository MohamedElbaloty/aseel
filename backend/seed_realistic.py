import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import app, USERS
from db.database import save_checkin, initialize_db

initialize_db()

visits_to_insert = [
    {
        "client_name": "maaden",
        "account_number": "m-001",
        "product": "RiCH",
        "stakeholder_name": "Ebtisam Al-Jarba - hr",
        "checkin_approach": "Proactive Check-In",
        "meeting_type": "On-Site Visit",
        "associated_mpr": True,
        "objectives_list": ["PoC Delivery", "Kick-Off Meeting"],
        "meeting_objective": "Discussing RiCH deployment updates and training.",
        "cs_dir_attended": False,
        "mpm_attended": True,
        "hesham_attended": False,
        "renewal_acct_mgr_attended": True,
        "sentiment": "Positive",
        "mom_generated": True,
        "mom_shared": True,
        "feedback_shared": True,
        "notes": "Ebtisam was very happy with the recent updates.",
        "follow_up_actions": ["Send technical proposal", "Schedule HR meeting"],
        "checkin_date": "2026-03-25",
        "checkin_start_time": "10:00",
        "checkin_end_time": "11:30",
        "next_visit_date": "2026-04-10"
    },
    {
        "client_name": "Mobily",
        "account_number": "mob-981",
        "product": "Ole5",
        "stakeholder_name": "Turki Aljawini - B2B Dir",
        "checkin_approach": "Reactive Check-In",
        "meeting_type": "Phone Call",
        "associated_mpr": False,
        "objectives_list": ["Feedback Collection", "Renewal Discussion"],
        "meeting_objective": "Quarterly review and feedback on Ole5 usage.",
        "cs_dir_attended": True,
        "mpm_attended": False,
        "hesham_attended": True,
        "renewal_acct_mgr_attended": False,
        "sentiment": "Neutral",
        "mom_generated": True,
        "mom_shared": False,
        "feedback_shared": True,
        "notes": "Requested some custom reports for B2B division.",
        "follow_up_actions": ["Check with tech team on custom reports"],
        "checkin_date": "2026-03-28",
        "checkin_start_time": "14:00",
        "checkin_end_time": "14:45",
        "next_visit_date": "2026-04-20"
    },
    {
        "client_name": "stc",
        "account_number": "stc-00',",
        "product": "Msegat",
        "stakeholder_name": "Faisal Alshammari - IT Manager",
        "checkin_approach": "Proactive Check-In",
        "meeting_type": "On-Line Meeting",
        "associated_mpr": True,
        "objectives_list": ["Demo / Presentation"],
        "meeting_objective": "Showcasing Msegat API integration features.",
        "cs_dir_attended": False,
        "mpm_attended": False,
        "hesham_attended": True,
        "renewal_acct_mgr_attended": False,
        "sentiment": "Positive",
        "mom_generated": True,
        "mom_shared": True,
        "feedback_shared": True,
        "notes": "Very interested in the new routing features.",
        "follow_up_actions": ["Share API documentation link", "Generate trial credentials"],
        "checkin_date": "2026-03-29",
        "checkin_start_time": "09:00",
        "checkin_end_time": "10:00",
        "next_visit_date": "2026-04-05"
    }
]

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
                
print("Finished Database Seeding on Railway!")
