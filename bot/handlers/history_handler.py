"""History handler - shows employee's recent check-ins."""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from db.database import get_employee_history
from datetime import datetime


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    records = get_employee_history(str(user.id), limit=5)

    if not records:
        await update.message.reply_text(
            "📭 لا يوجد لديك سجلات check-in حتى الآن.\n"
            "أرسل لي تفاصيل أي اجتماع لبدء التسجيل."
        )
        return

    lines = [f"📋 *آخر {len(records)} زيارات لك:*\n"]
    for i, r in enumerate(records, 1):
        dt = r.get("created_at", "")
        try:
            dt_fmt = datetime.fromisoformat(dt).strftime("%Y-%m-%d")
        except Exception:
            dt_fmt = dt

        synced = "✅" if r.get("synced_to_sheet") else "💾"
        lines.append(
            f"*{i}.* {synced} *{r.get('client_name') or 'عميل غير محدد'}*\n"
            f"   📅 {dt_fmt} | 📦 {r.get('product') or '–'}\n"
            f"   🎯 {(r.get('visit_reason') or '–')[:60]}"
        )

    legend = "\n\n✅ = محفوظ في Sheets  |  💾 = محفوظ محلياً"
    await update.message.reply_text(
        "\n\n".join(lines) + legend,
        parse_mode=ParseMode.MARKDOWN,
    )
