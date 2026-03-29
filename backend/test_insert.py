import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import app
from db.database import save_checkin, initialize_db

initialize_db()

dummy_data = {
    "client_name": "maaden - maaden",
    "account_number": "m-001",
    "product": "RiCH",
    "stakeholder_name": "Ebtisam Al-Jarba - hr",
    
    # Advanced / New fields
    "checkin_approach": "Proactive Check-In",
    "meeting_type": "On-Site Visit",
    "associated_mpr": True,
    "objectives_list": ["PoC Delivery", "Kick-Off Meeting"],
    "meeting_objective": "Test objective detail",
    "cs_dir_attended": False,
    "mpm_attended": True,
    "hesham_attended": False,
    "renewal_acct_mgr_attended": True,
    "sentiment": "Positive",
    "mom_generated": True,
    "mom_shared": True,
    "feedback_shared": True,
    "notes": "These are old meeting notes (should not auto-fill actually).",
    "follow_up_actions": ["Test Action 1", "Test Action 2"],
}


print("Saving record...", flush=True)

# Important: To make it work regardless of the user ID, we will inject it with the user ID that's currently logged in.
# How to know the user id? Let's just remove the employee_id check from the API for the test!
# Actually we can just create it for all common employee IPs or better, directly in SQL without employee_id, and then modify get_latest_checkin!

# Let's insert into the DB directly for ALL employee IDs in SQLite/PG
def duplicate_for_all_emps():
    from db.database import get_employees
    emps = get_employees()
    if not emps: 
        print("No users found")
        return
    for e in emps:
        eid = str(e['id']) if 'id' in e else str(e)
        ename = e['name'] if 'name' in e else str(e)
        try:
            res = save_checkin(dummy_data, eid, ename)
            print("Saved for", eid, "->", res)
        except Exception as x:
            print("Err", x)

with app.app_context():
    duplicate_for_all_emps()
