"""
Main check-in conversation handler for the Telegram Bot.
"""
import logging
import json
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from ai.extractor import extract_checkin_data, format_extracted_data, transcribe_audio
from sheets.writer import save_to_sheet
from db.database import save_checkin, mark_synced

logger = logging.getLogger(__name__)

CONFIRMING = 1
EDITING = 2

EDITABLE_FIELDS = {
    "client_name": "👤 اسم العميل",
    "account_number": "🔢 رقم الحساب",
    "product": "📦 المنتج",
    "visit_reason": "🎯 سبب الزيارة",
    "meeting_type": "📞 نوع الاجتماع",
    "account_manager_present": "👔 مدير الحساب",
    "admin_manager_present": "🏛️ مدير الإدارة",
    "meeting_datetime": "📅 تاريخ الاجتماع",
    "meeting_objective": "🏆 هدف الاجتماع",
    "next_visit_date": "📆 الزيارة القادمة",
    "notes": "📝 ملاحظات",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = (
        f"👋 أهلاً *{user.first_name}*!\n\n"
        "أنا بوت *Post Check-in* الذكي.\n\n"
        "📌 *كيف يعمل النظام:*\n"
        "فقط أرسل لي تفاصيل اجتماعك (رسالة نصية أو بصمة صوت) بأي لغة — عربي أو إنجليزي — "
        "وسأقوم تلقائياً باستخراج بيانات الـ Check-in وحفظها.\n\n"
        "💬 *مثال:*\n"
        "_زرت العميل شركة الأفق اليوم الساعة 2 ظهراً بخصوص منتج تمويل الأعمال. "
        "كان مدير الحساب حاضراً. الهدف كان مناقشة تجديد العقد. "
        "الزيارة القادمة بعد أسبوعين._\n\n"
        "📋 الأوامر المتاحة:\n"
        "/history - عرض آخر زياراتك\n"
        "/help - المساعدة\n"
        "/cancel - إلغاء العملية الحالية"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming message and extract check-in data using AI."""
    user = update.effective_user

    try:
        # Check if message has voice or audio
        if update.message.voice or update.message.audio:
            processing_msg = await update.message.reply_text(
                "🎙️ *جاري تفريغ الصوت وتحليله بالذكاء الاصطناعي...*",
                parse_mode=ParseMode.MARKDOWN,
            )
            audio_source = update.message.voice or update.message.audio
            file = await context.bot.get_file(audio_source.file_id)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
                temp_audio_path = temp_audio.name
            
            await file.download_to_drive(temp_audio_path)
                
            try:
                raw_message = transcribe_audio(temp_audio_path)
            finally:
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                    
            await processing_msg.edit_text(
                "🔄 *جاري تحليل النص المستخرج بالذكاء الاصطناعي...*",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            raw_message = update.message.text
            processing_msg = await update.message.reply_text(
                "🔄 *جاري تحليل رسالتك بالذكاء الاصطناعي...*",
                parse_mode=ParseMode.MARKDOWN,
            )

        # AI extraction
        extracted = extract_checkin_data(raw_message)

        # Store in context
        context.user_data["extracted"] = extracted
        context.user_data["raw_message"] = raw_message
        context.user_data["employee_name"] = user.full_name
        context.user_data["employee_id"] = str(user.id)

        # Format and send extracted data
        formatted = format_extracted_data(extracted)

        keyboard = [
            [
                InlineKeyboardButton("✅ تأكيد وحفظ", callback_data="confirm"),
                InlineKeyboardButton("✏️ تعديل", callback_data="edit"),
            ],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.delete()
        await update.message.reply_text(
            formatted + "\n\n_هل البيانات صحيحة؟_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

        return CONFIRMING

    except Exception as e:
        logger.error(f"AI extraction error: {e}")
        await processing_msg.edit_text(
            "⚠️ حدث خطأ أثناء تحليل الرسالة. يرجى المحاولة مرة أخرى أو إعادة صياغة النص.",
        )
        return ConversationHandler.END


async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirm/edit/cancel callbacks."""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "confirm":
        await query.edit_message_reply_markup(None)
        saving_msg = await query.message.reply_text("💾 *جاري الحفظ...*", parse_mode=ParseMode.MARKDOWN)

        extracted = context.user_data.get("extracted", {})
        employee_name = context.user_data.get("employee_name", "Unknown")
        employee_id = context.user_data.get("employee_id", "0")
        raw_message = context.user_data.get("raw_message", "")

        # Save to SQLite
        record_id = save_checkin(extracted, employee_id, employee_name, raw_message)

        # Try to save to Google Sheets
        sheet_saved = save_to_sheet(extracted, employee_name, employee_id)
        if sheet_saved:
            mark_synced(record_id)

        sheet_status = "✅ تم الحفظ في Google Sheets" if sheet_saved else "⚠️ تعذّر الحفظ في Sheets (محفوظ محلياً)"

        await saving_msg.edit_text(
            f"🎉 *تم حفظ بيانات Check-in بنجاح!*\n\n"
            f"📁 *رقم السجل:* #{record_id}\n"
            f"{sheet_status}\n\n"
            f"شكراً {employee_name}! استمر في إرسال تقاريرك 💪",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data.clear()
        return ConversationHandler.END

    elif action == "edit":
        keyboard = [
            [InlineKeyboardButton(label, callback_data=f"editfield_{key}")]
            for key, label in EDITABLE_FIELDS.items()
        ]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
        await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))
        return EDITING

    elif action == "cancel":
        await query.edit_message_text("❌ تم إلغاء العملية.")
        context.user_data.clear()
        return ConversationHandler.END


async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selects which field to edit."""
    query = update.callback_query
    await query.answer()

    if query.data == "back":
        extracted = context.user_data.get("extracted", {})
        formatted = format_extracted_data(extracted)
        keyboard = [
            [
                InlineKeyboardButton("✅ تأكيد وحفظ", callback_data="confirm"),
                InlineKeyboardButton("✏️ تعديل", callback_data="edit"),
            ],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")],
        ]
        await query.edit_message_text(
            formatted + "\n\n_هل البيانات صحيحة؟_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRMING

    if query.data.startswith("editfield_"):
        field = query.data.replace("editfield_", "")
        context.user_data["editing_field"] = field
        field_label = EDITABLE_FIELDS.get(field, field)

        current_val = context.user_data.get("extracted", {}).get(field)
        hint = ""
        if field in ("account_manager_present", "admin_manager_present"):
            hint = "\n\n💡 أرسل: `نعم` أو `لا`"
        elif field == "meeting_type":
            hint = "\n\n💡 أرسل: `حضوري` أو `مكالمة` أو `اونلاين`"
        elif field in ("meeting_datetime", "next_visit_date"):
            hint = "\n\n💡 أرسل: `YYYY-MM-DD HH:MM` مثال: `2024-03-28 14:00`"

        await query.edit_message_text(
            f"✏️ *تعديل: {field_label}*\n\n"
            f"القيمة الحالية: `{current_val or 'غير محدد'}`\n\n"
            f"أرسل القيمة الجديدة:{hint}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return EDITING


async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the new field value entered by user."""
    field = context.user_data.get("editing_field")
    if not field:
        return EDITING

    new_value_raw = update.message.text.strip()
    extracted = context.user_data.get("extracted", {})

    # Type coercion
    if field in ("account_manager_present", "admin_manager_present"):
        new_value = True if new_value_raw in ("نعم", "yes", "1", "true") else False
    elif field == "meeting_type":
        mapping = {"حضوري": "in_person", "مكالمة": "phone_call", "اونلاين": "online"}
        new_value = mapping.get(new_value_raw, new_value_raw)
    elif field in ("meeting_datetime", "next_visit_date"):
        try:
            from datetime import datetime
            dt = datetime.strptime(new_value_raw, "%Y-%m-%d %H:%M")
            new_value = dt.isoformat()
        except ValueError:
            new_value = new_value_raw
    else:
        new_value = new_value_raw

    extracted[field] = new_value
    context.user_data["extracted"] = extracted
    context.user_data.pop("editing_field", None)

    formatted = format_extracted_data(extracted)
    keyboard = [
        [
            InlineKeyboardButton("✅ تأكيد وحفظ", callback_data="confirm"),
            InlineKeyboardButton("✏️ تعديل", callback_data="edit"),
        ],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")],
    ]
    await update.message.reply_text(
        formatted + "\n\n_هل البيانات صحيحة؟_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CONFIRMING


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ تم إلغاء العملية. أرسل تفاصيل اجتماعك في أي وقت.")
    return ConversationHandler.END
