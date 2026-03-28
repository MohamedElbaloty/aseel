import json, os
from datetime import datetime

_client = None

def get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            raise ValueError('OPENAI_API_KEY غير معيّن في ملف .env')
        _client = OpenAI(api_key=key)
    return _client

SYSTEM_PROMPT = """You are an AI assistant extracting structured post-visit check-in data from free-text messages (Arabic, English, or mixed).

Extract these fields (use null if not mentioned):
- client_name: Client/company name
- account_number: Account ID or number
- product: Product or service discussed
- visit_reason: Reason/purpose of visit
- account_manager_present: boolean
- admin_manager_present: boolean
- meeting_datetime: ISO 8601 (use today's date if only time given)
- meeting_objective: Main goal of the meeting
- next_visit_date: ISO 8601 if mentioned
- meeting_type: "in_person" | "phone_call" | "online"
- notes: Additional notes
- follow_up_actions: Array of action items

Today: {today}

Return ONLY valid JSON with these exact field names."""

def extract_checkin_data(message: str) -> dict:
    today = datetime.now().strftime('%Y-%m-%d')
    resp = get_client().chat.completions.create(
        model='gpt-4o',
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT.format(today=today)},
            {'role': 'user', 'content': message}
        ],
        temperature=0.1,
        max_tokens=600,
        response_format={'type': 'json_object'}
    )
    return json.loads(resp.choices[0].message.content)
