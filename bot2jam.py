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
    ContextTypes,
    CallbackQueryHandler,
    PicklePersistence,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.environ.get("TOKEN") or "YOUR_BOT_TOKEN_HERE"
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")  # ex: https://yourapp.onrender.com
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None

persistence = PicklePersistence(filepath="reminder_data.pkl")
user_jobs = {}  # Simpan job per chat
active_sections = {}  # Simpan status aktif dari kategori per chat
timezone = pytz.timezone("Asia/Jakarta")

# Jadwal pengingat otomatis: (jam, menit, pesan, kategori)
reminder_schedule = [
    (7, 5, "07:05 cek link pc indo", "pagi"),
    (7, 0, "07:00 cek phising", "pagi"),
    (7, 5, "07:05 cek dana PGA BL", "pagi"),
    (7, 15, "07:15 req dana PGA", "pagi"),
    (7, 30, "07:30 paito berita", "pagi"),
    (8, 0, "08:00 total depo", "pagi"),
    (8, 0, "08:00 Slot Harian", "pagi"),
    (8, 0, "08:00 jadwalkan bukti jp ke jam 10.00", "pagi"),
    (8, 10, "08:10 BC link alternatif ke jam 12.00", "pagi"),
    (9, 0, "09:00 jowo pools", "pagi"),
    (9, 10, "09:10 TO semua pasaran", "pagi"),
    (9, 30, "09:30 Audit BCA", "pagi"),
    (9, 45, "09:45 First Register", "pagi"),
    (10, 0, "10:00 BC maintenance done (kamis)", "pagi"),
    (10, 0, "10:00 cek data selisih", "pagi"),
    (10, 0, "10:00 total depo", "pagi"),
    (10, 30, "10:30 isi data bola (> jam 1)", "pagi"),
    (11, 0, "11:00 bc maintenance WL (selasa)", "pagi"),
    (11, 0, "11:00 bc jadwal bola", "pagi"),
    (12, 0, "12:00 total depo", "pagi"),
    (12, 0, "12:00 slot & rng mingguan", "pagi"),
    (12, 50, "12:50 live ttm", "pagi"),
    (12, 30, "12:30 cek phising", "pagi"),
    (13, 0, "13:00 wd report", "pagi"),
    (13, 0, "13:00 BC Result Toto Macau", "pagi"),
    (13, 30, "13:30 slot & rng harian", "pagi"),
    (14, 0, "14:00 BC Result Sydney", "pagi"),
    (14, 0, "14:00 depo harian", "pagi"),

    (15, 30, "15:30 cek link", "siang"),
    (16, 0, "16:00 cek phising", "siang"),
    (16, 0, "16:00 deposit harian", "siang"),
    (16, 30, "16:30 jadwalkan bukti jp ke jam 17.00", "siang"),
    (16, 0, "16:00 isi data selisih", "siang"),
    (16, 0, "16:00 BC Result Toto Macau", "siang"),
    (17, 40, "17:40 SLOT harian (kalau tidak ada sgp jam 18.30)", "siang"),
    (17, 50, "17:50 BC Result Singapore", "siang"),
    (18, 0, "18:00 5 lucky ball", "siang"),
    (18, 0, "18:00 deposit harian", "siang"),
    (18, 5, "18:05 BC link alt ke jam 19.00", "siang"),
    (18, 10, "18:10 isi data wlb2c", "siang"),
    (19, 0, "19:00 BC Result Toto Macau", "siang"),
    (19, 30, "19:30 Audit BCA", "siang"),
    (19, 45, "19:45 First Register", "siang"),
    (20, 0, "20:00 deposit harian", "siang"),
    (21, 0, "21:00 jowo pools", "siang"),
    (21, 0, "21:00 cek phising", "siang"),
    (21, 0, "21:00 wd report", "siang"),
    (22, 0, "22:00 BC Result Toto Macau", "siang"),
    (22, 0, "22:00 deposit harian", "siang"),
    (22, 45, "22:45 Slot harian", "siang"),

    (23, 0, "23:00 SLOT harian", "malam"),
    (23, 10, "23:10 BC Result Hongkong", "malam"),
    (23, 30, "23:30 cek link & cek phising", "malam"),
    (23, 30, "23:30 BC rtp slot jam 00.10", "malam"),
    (23, 40, "23:40 depo harian", "malam"),
    (0, 5, "00:05 BC Result Toto Macau", "malam"),
    (0, 1, "00:01 update total bonus", "malam"),
    (0, 30, "00:30 BC link alt jam 5", "malam"),
    (0, 30, "00:30 BC bukti JP jam 4", "malam"),
    (0, 30, "00:30 BC maintenance mingguan ke jam 4 (kamis)", "malam"),
    (0, 45, "00:45 slot harian", "malam"),
    (1, 0, "01:00 isi biaya pulsa / isi akuran (senin subuh)", "malam"),
    (1, 30, "01:30 isi data promo", "malam"),
    (2, 0, "02:00 total depo", "malam"),
    (2, 0, "02:00 cek pl config", "malam"),
    (3, 30, "03:30 Audit BCA", "malam"),
    (3, 45, "03:45 First Register", "malam"),
    (4, 0, "04:00 total depo", "malam"),
    (5, 0, "05:00 cek phising", "malam"),
    (5, 0, "05:00 wd report", "malam"),
    (5, 0, "05:00 Slot harian", "malam"),
    (5, 45, "05:45 total depo", "malam"),
]

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    message = data["message"]
    thread_id = data.get("thread_id")
    await context.bot.send_message(chat_id=chat_id, message_thread_id=thread_id, text=f"🔔 {message}")

def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌅 Pagi", callback_data="pagi"),
         InlineKeyboardButton("🏙️ Siang", callback_data="siang"),
         InlineKeyboardButton("🌃 Malam", callback_data="malam")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pilih waktu jadwal yang ingin kamu aktifkan:", reply_markup=get_keyboard())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data
    chat_id = query.message.chat.id
    thread_id = query.message.message_thread_id
    buttons = [
        [InlineKeyboardButton("✅ Aktifkan", callback_data=f"aktif_{section}"),
         InlineKeyboardButton("❌ Reset", callback_data=f"reset_{section}")]
    ]
    items = [f"{h:02d}:{m:02d} - {msg}" for h, m, msg, cat in reminder_schedule if cat == section]
    text = f"📋 Jadwal {section}:
" + "\n".join(items)
    markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, reply_markup=markup)

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, section = query.data.split("_")
    chat_id = query.message.chat.id
    thread_id = query.message.message_thread_id

    if action == "aktif":
        await schedule_section_reminders(context.application, chat_id, section, thread_id)
        await query.edit_message_text(f"✅ Jadwal {section} diaktifkan.")
    elif action == "reset":
        reset_section_reminders(chat_id, section)
        await query.edit_message_text(f"❌ Jadwal {section} dihentikan.")

async def schedule_section_reminders(application, chat_id, section, thread_id):
    key = f"{chat_id}_{section}"
    if key in user_jobs:
        for job in user_jobs[key]:
            job.schedule_removal()
    jobs = []
    for h, m, msg, cat in reminder_schedule:
        if cat != section:
            continue
        waktu = datetime.time(hour=h, minute=m, tzinfo=timezone)
        job = application.job_queue.run_daily(
            reminder,
            time=waktu,
            chat_id=chat_id,
            name=f"reminder_{key}_{h:02d}{m:02d}",
            data={"chat_id": chat_id, "message": msg, "thread_id": thread_id}
        )
        jobs.append(job)
    user_jobs[key] = jobs

def reset_section_reminders(chat_id, section):
    key = f"{chat_id}_{section}"
    if key in user_jobs:
        for job in user_jobs[key]:
            job.schedule_removal()
        del user_jobs[key]

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("❗ Exception occurred:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, text="⚠️ Terjadi kesalahan. Silakan coba lagi nanti.")
        except Exception:
            pass

async def start_jobqueue(app):
    await app.job_queue.start()
    logging.info("✅ JobQueue dimulai.")

async def handle_root(request):
    return web.Response(text="Bot is running")

async def handle_webhook(request):
    application = request.app["application"]
    update = await request.json()
    from telegram import Update as TgUpdate
    tg_update = TgUpdate.de_json(update, application.bot)
    await application.update_queue.put(tg_update)
    return web.Response()

async def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence)
        .post_init(start_jobqueue)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(pagi|siang|malam)$"))
    application.add_handler(CallbackQueryHandler(handle_action, pattern="^(aktif|reset)_(pagi|siang|malam)$"))
    application.add_error_handler(error_handler)

    app = web.Application()
    app["application"] = application
    app.add_routes([
        web.get("/", handle_root),
        web.post(WEBHOOK_PATH, handle_webhook),
    ])

    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        logging.info(f"🌐 Webhook diset ke {WEBHOOK_URL}")
    else:
        logging.warning("⚠️ WEBHOOK_URL_BASE environment variable tidak diset, webhook tidak aktif!")

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Webserver berjalan di port {port}")

    await application.initialize()
    await application.start()

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
