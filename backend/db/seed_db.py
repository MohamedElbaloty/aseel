import os
import sys
import pandas as pd
import json
import math

sys.path.insert(0, os.path.dirname(__file__))
from database import get_pg

def clean_val(val):
    if pd.isna(val) or val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val).strip()

def seed_database():
    print("Connecting to database...")
    conn = get_pg()
    
    db_folder = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database')
    profiling_path = os.path.join(db_folder, 'Customer Stakeholder Profiling (Responses).xlsx')
    
    df_prof = pd.read_excel(profiling_path)
    print("Read excel successfully. Inserting stakeholders...")
    
    sh_sql = """
        INSERT INTO stakeholders (farabi_account, stakeholder_name, stakeholder_title, email, mobile_number, influence_level)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE stakeholders RESTART IDENTITY;")
        
    stakeholder_data = []
    for index, row in df_prof.iterrows():
        farabi = clean_val(row.get("Customer's Farabi Account Number"))
        s_name = clean_val(row.get('Stakeholder Name'))
        if farabi and s_name:
            stakeholder_data.append((
                farabi,
                s_name,
                clean_val(row.get('Stakeholder Title')),
                clean_val(row.get('eMail')),
                clean_val(row.get('Mobile Number')),
                clean_val(row.get('Influence Level'))
            ))
            
    print(f"Executing batch insert of {len(stakeholder_data)} stakeholders...")
    with conn.cursor() as cur:
        cur.executemany(sh_sql, stakeholder_data)
    conn.commit()
    conn.close()
    print("Stakeholders seeded successfully.")

if __name__ == '__main__':
    seed_database()
