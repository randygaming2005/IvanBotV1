import logging
import datetime
import pytz
import os
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.environ.get("TOKEN") or "YOUR_BOT_TOKEN_HERE"
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None

persistence = PicklePersistence(filepath="reminder_data.pkl")
user_jobs = {}
timezone = pytz.timezone("Asia/Jakarta")

REMINDER_SECTIONS = {
    "Pagi": [
        (7, 5, "07:05 cek link pc indo"),
        (7, 0, "07:00 cek phising"),
        (7, 5, "07:05 cek dana PGA BL"),
        (7, 15, "07:15 req dana PGA"),
        (7, 30, "07:30 paito berita"),
        (8, 0, "08:00 total depo"),
        (8, 0, "08:00 Slot Harian"),
        (8, 0, "08:00 jadwalkan bukti jp ke jam 10.00"),
        (8, 10, "08:10 BC link alternatif ke jam 12.00"),
        (9, 0, "09:00 jowo pools"),
        (9, 10, "09:10 TO semua pasaran"),
        (9, 30, "09:30 Audit BCA"),
        (9, 45, "09:45 First Register"),
        (10, 0, "10:00 BC maintenance done (kamis)"),
        (10, 0, "10:00 cek data selisih"),
        (10, 0, "10:00 total depo"),
        (10, 30, "10:30 isi data bola (> jam 1)"),
        (11, 0, "11:00 bc maintenance WL (selasa)"),
        (11, 0, "11:00 bc jadwal bola"),
        (12, 0, "12:00 total depo"),
        (12, 0, "12:00 slot & rng mingguan"),
        (12, 50, "12:50 live ttm"),
        (12, 30, "12:30 cek phising"),
        (13, 0, "13:00 wd report"),
        (13, 0, "13:00 BC Result Toto Macau"),
        (13, 30, "13:30 slot & rng harian"),
        (14, 0, "14:00 BC Result Sydney"),
        (14, 0, "14:00 depo harian"),
    ],
    "Siang": [
        (15, 30, "15:30 cek link"),
        (16, 0, "16:00 cek phising"),
        (16, 0, "16:00 deposit harian"),
        (16, 30, "16:30 jadwalkan bukti jp ke jam 17.00"),
        (16, 0, "16:00 isi data selisih"),
        (16, 0, "16:00 BC Result Toto Macau"),
        (17, 40, "17:40 SLOT harian (kalau tidak ada sgp jam 18.30)"),
        (17, 50, "17:50 BC Result Singapore"),
        (18, 0, "18:00 5 lucky ball"),
        (18, 0, "18:00 deposit harian"),
        (18, 5, "18:05 BC link alt ke jam 19.00"),
        (18, 10, "18:10 isi data wlb2c"),
        (19, 0, "19:00 BC Result Toto Macau"),
        (19, 30, "19:30 Audit BCA"),
        (19, 45, "19:45 First Register"),
        (20, 0, "20:00 deposit harian"),
        (21, 0, "21:00 jowo pools"),
        (21, 0, "21:00 cek phising"),
        (21, 0, "21:00 wd report"),
        (22, 0, "22:00 BC Result Toto Macau"),
        (22, 0, "22:00 deposit harian"),
        (22, 45, "22:45 Slot harian"),
    ],
    "Malam": [
        (23, 0, "23:00 SLOT harian"),
        (23, 10, "23:10 BC Result Hongkong"),
        (23, 30, "23:30 cek link & cek phising"),
        (23, 30, "23:30 BC rtp slot jam 00.10"),
        (23, 40, "23:40 depo harian"),
        (0, 5, "00:05 BC Result Toto Macau"),
        (0, 1, "00:01 update total bonus"),
        (0, 30, "00:30 BC link alt jam 5"),
        (0, 30, "00:30 BC bukti JP jam 4"),
        (0, 30, "00:30 BC maintenance mingguan ke jam 4 (kamis)"),
        (0, 45, "00:45 slot harian"),
        (1, 0, "01:00 isi biaya pulsa / isi akuran (senin subuh)"),
        (1, 30, "01:30 isi data promo"),
        (2, 0, "02:00 total depo"),
        (2, 0, "02:00 cek pl config"),
        (3, 30, "03:30 Audit BCA"),
        (3, 45, "03:45 First Register"),
        (4, 0, "04:00 total depo"),
        (5, 0, "05:00 cek phising"),
        (5, 0, "05:00 wd report"),
        (5, 0, "05:00 Slot harian"),
        (5, 45, "05:45 total depo"),
    ],
}

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    message = data["message"]
    section = data["section"]
    thread_id = data.get("thread_id")

    completed_tasks = context.bot_data.get("completed_tasks", {}).get(chat_id, set())
    if message in completed_tasks:
        return

    active_sections = context.bot_data.get("active_sections", {}).get(chat_id, {})
    if not active_sections.get(section):
        return

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=f"🔔 {message}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Pagi", callback_data="section_Pagi")],
        [InlineKeyboardButton("Siang", callback_data="section_Siang")],
        [InlineKeyboardButton("Malam", callback_data="section_Malam")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("🕒 Pilih bagian jadwal untuk dikendalikan:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("🕒 Pilih bagian jadwal untuk dikendalikan:", reply_markup=reply_markup)

async def section_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_", 1)[1]
    chat_id = query.message.chat.id

    if section == "menu":
        # Tampilkan menu utama kembali
        keyboard = [
            [InlineKeyboardButton("Pagi", callback_data="section_Pagi")],
            [InlineKeyboardButton("Siang", callback_data="section_Siang")],
            [InlineKeyboardButton("Malam", callback_data="section_Malam")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🕒 Pilih bagian jadwal untuk dikendalikan:", reply_markup=reply_markup)
        return

    if section not in REMINDER_SECTIONS:
        await query.edit_message_text("⚠️ Bagian jadwal tidak ditemukan.")
        return

    completed = context.bot_data.get("completed_tasks", {}).get(chat_id, set())

    keyboard = [[InlineKeyboardButton("✅ Aktifkan", callback_data=f"activate_{section}")]]
    for h, m, msg in REMINDER_SECTIONS[section]:
        status = "✅" if msg in completed else "❌"
        keyboard.append([InlineKeyboardButton(f"{status} {h:02d}:{m:02d} - {msg}", callback_data=f"done_{section}_{msg}")])

    keyboard.append([InlineKeyboardButton("❌ Reset", callback_data=f"reset_{section}")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="section_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📋 Jadwal {section}:", reply_markup=reply_markup)

async def activate_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_")[1]
    chat_id = query.message.chat.id

    context.bot_data.setdefault("active_sections", {}).setdefault(chat_id, {})[section] = True
    await schedule_section_reminders(context.application, chat_id, section)
    await query.edit_message_text(f"✅ Pengingat untuk bagian *{section}* telah diaktifkan.", parse_mode='Markdown')

async def reset_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_")[1]
    chat_id = query.message.chat.id

    if chat_id in user_jobs:
        for job in user_jobs[chat_id][:]:
            if job.data.get("section") == section:
                job.schedule_removal()
                user_jobs[chat_id].remove(job)

    context.bot_data.get("active_sections", {}).get(chat_id, {}).pop(section, None)
    await query.edit_message_text(f"❌ Pengingat untuk bagian *{section}* telah dihentikan.", parse_mode='Markdown')

async def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, section, msg = query.data.split("_", 2)
    chat_id = query.message.chat.id

    completed_tasks = context.bot_data.setdefault("completed_tasks", {}).setdefault(chat_id, set())

    if msg in completed_tasks:
        completed_tasks.remove(msg)
    else:
        completed_tasks.add(msg)

    await section_handler(update, context)

async def schedule_section_reminders(application, chat_id, section, thread_id=None):
    # Hapus job lama
    if chat_id in user_jobs:
        for job in user_jobs[chat_id][:]:
            if job.data.get("section") == section:
                job.schedule_removal()
                user_jobs[chat_id].remove(job)

    user_jobs.setdefault(chat_id, [])

    for hour, minute, msg in REMINDER_SECTIONS[section]:
        now = datetime.datetime.now(tz=timezone)
        reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if reminder_time < now:
            reminder_time += datetime.timedelta(days=1)

        delta = (reminder_time - now).total_seconds()

        job = application.job_queue.run_once(
            reminder,
            delta,
            data={"chat_id": chat_id, "message": msg, "section": section, "thread_id": thread_id},
            name=f"{chat_id}_{section}_{msg}",
        )
        user_jobs[chat_id].append(job)

async def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(section_handler, pattern=r"^section_"))
    application.add_handler(CallbackQueryHandler(activate_section, pattern=r"^activate_"))
    application.add_handler(CallbackQueryHandler(reset_section, pattern=r"^reset_"))
    application.add_handler(CallbackQueryHandler(mark_done, pattern=r"^done_"))

    if WEBHOOK_URL_BASE:
        # Webhook mode
        await application.bot.set_webhook(WEBHOOK_URL)
        runner = web.AppRunner(application.bot.web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", "8443")))
        await site.start()
        print("Bot started in webhook mode")
        while True:
            await asyncio.sleep(3600)
    else:
        # Polling mode
        print("Bot started in polling mode")
        await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
