"""
AI Extractor - Uses OpenAI GPT to extract structured check-in data from free text.
Supports Arabic and English messages.
"""
import json
import os
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an AI assistant that extracts structured data from post-visit check-in messages written by sales or account managers. The messages can be in Arabic or English or a mix.

Extract the following fields from the message. If a field is not mentioned, use null.

Fields:
- client_name: The name of the client or company visited
- account_number: Client account number or ID (if mentioned)
- product: The product or service discussed
- visit_reason: The reason or purpose of the visit
- account_manager_present: Boolean - was the account manager present (true/false/null)
- admin_manager_present: Boolean - was the admin/branch manager present (true/false/null)
- meeting_datetime: Date and time of the meeting (ISO 8601 format, use today if only time given)
- meeting_objective: The main goal or objective of the meeting
- next_visit_date: Scheduled date of the next visit (ISO 8601 format if mentioned)
- meeting_type: "in_person", "phone_call", or "online" - detect from context
- notes: Any additional relevant notes
- follow_up_actions: List of action items or follow-up tasks mentioned

Today's date for reference: {today}

Return ONLY valid JSON with exactly these field names. No markdown, no explanation. Example:
{{
  "client_name": "شركة الأفق",
  "account_number": "ACC-1234",
  "product": "تمويل الأعمال",
  "visit_reason": "مناقشة تجديد العقد",
  "account_manager_present": true,
  "admin_manager_present": false,
  "meeting_datetime": "2024-03-28T14:00:00",
  "meeting_objective": "إتمام تجديد عقد التمويل والاتفاق على الشروط الجديدة",
  "next_visit_date": "2024-04-10T10:00:00",
  "meeting_type": "in_person",
  "notes": "العميل مهتم بزيادة حد الائتمان",
  "follow_up_actions": ["إرسال عرض سعر محدث", "جدولة اجتماع مع قسم المخاطر"]
}}"""


def extract_checkin_data(user_message: str) -> dict:
    """
    Sends a user message to OpenAI and extracts structured check-in data.
    Returns a dict with the extracted fields.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = SYSTEM_PROMPT.format(today=today)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)
    return data

def transcribe_audio(file_path: str) -> str:
    """
    Transcribes an audio file (voice note) using OpenAI Whisper.
    """
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
        )
    return transcription.text

def format_extracted_data(data: dict) -> str:
    """
    Format extracted data for Telegram message display (Arabic-first).
    """
    def v(val, yes="✅ نعم", no="❌ لا"):
        if val is True:
            return yes
        if val is False:
            return no
        return "➖ غير محدد"

    def fmt_date(dt_str):
        if not dt_str:
            return "➖ غير محدد"
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return dt_str

    meeting_type_map = {
        "in_person": "🏢 حضوري",
        "phone_call": "📞 مكالمة هاتفية",
        "online": "💻 أونلاين",
        None: "➖ غير محدد",
    }

    actions = data.get("follow_up_actions") or []
    actions_text = "\n".join(f"  • {a}" for a in actions) if actions else "  ➖ لا يوجد"

    lines = [
        "📋 *بيانات Post Check-in المستخرجة*",
        "─────────────────────────",
        f"👤 *العميل:* {data.get('client_name') or '➖ غير محدد'}",
        f"🔢 *رقم الحساب:* {data.get('account_number') or '➖ غير محدد'}",
        f"📦 *المنتج:* {data.get('product') or '➖ غير محدد'}",
        f"🎯 *سبب الزيارة:* {data.get('visit_reason') or '➖ غير محدد'}",
        f"📞 *نوع الاجتماع:* {meeting_type_map.get(data.get('meeting_type'))}",
        f"👔 *مدير الحساب:* {v(data.get('account_manager_present'))}",
        f"🏛️ *مدير الإدارة:* {v(data.get('admin_manager_present'))}",
        f"📅 *تاريخ الاجتماع:* {fmt_date(data.get('meeting_datetime'))}",
        f"🏆 *هدف الاجتماع:* {data.get('meeting_objective') or '➖ غير محدد'}",
        f"📆 *الزيارة القادمة:* {fmt_date(data.get('next_visit_date'))}",
        f"📝 *ملاحظات:* {data.get('notes') or '➖ لا يوجد'}",
        f"✔️ *متابعات:*\n{actions_text}",
        "─────────────────────────",
    ]

    return "\n".join(lines)
