import logging
import datetime
import pytz
import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
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
timezone = pytz.timezone("Asia/Jakarta")

# Jadwal pengingat otomatis: (jam, menit, pesan)
reminder_schedule = [
    # Pagi
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

    # Siang
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

    # Malam
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
]

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    message = data["message"]
    thread_id = data.get("thread_id")

    logging.info(f"🔔 Mengirim pengingat ke chat_id {chat_id}: {message}")
    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=f"🔔 {message}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    # Jadwalkan semua pengingat otomatis untuk user ini
    await schedule_all_reminders(context.application, chat_id, thread_id)

    await update.message.reply_text(
        "👋 Halo! Bot ini otomatis mengingatkan sesuai jadwal yang sudah ditentukan.\n"
        "Gunakan /list untuk melihat jadwal pengingat."
    )

async def list_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msgs = []
    for h, m, msg in reminder_schedule:
        msgs.append(f"{h:02d}:{m:02d} - {msg}")
    await update.message.reply_text("📋 Jadwal pengingat otomatis:\n" + "\n".join(msgs))

async def schedule_all_reminders(application, chat_id, thread_id=None):
    # Bersihkan dulu job lama kalau ada
    if chat_id in user_jobs:
        for job in user_jobs[chat_id]:
            job.schedule_removal()
        user_jobs.pop(chat_id)

    jobs = []
    for h, m, msg in reminder_schedule:
        waktu = datetime.time(hour=h, minute=m, tzinfo=timezone)
        job = application.job_queue.run_daily(
            reminder,
            time=waktu,
            chat_id=chat_id,
            name=f"reminder_{chat_id}_{h:02d}{m:02d}",
            data={"chat_id": chat_id, "message": msg, "thread_id": thread_id}
        )
        jobs.append(job)
        logging.info(f"✅ Menjadwalkan pengingat {h:02d}:{m:02d} untuk chat_id {chat_id}")

    user_jobs[chat_id] = jobs

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
    application.add_handler(CommandHandler("list", list_times))
    application.add_error_handler(error_handler)

    # Setup aiohttp webserver dengan webhook dan healthcheck
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

    # Bot siap jalan, loop infinite supaya tidak exit
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
