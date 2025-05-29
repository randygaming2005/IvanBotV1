import logging
import asyncio
from datetime import time
from pytz import timezone
from telegram import Update, ForceReply
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    Application, CallbackContext
)
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Timezone
TZ = timezone("Asia/Jakarta")

# Jadwal Pagi
JADWAL_PAGI = [
    ("07:00", "cek phising"),
    ("07:05", "cek link pc indo"),
    ("07:05", "cek dana PGA BL"),
    ("07:15", "req dana PGA"),
    ("07:30", "paito berita"),
    ("08:00", "total depo"),
    ("08:00", "Slot Harian"),
    ("08:00", "jadwalkan bukti jp ke jam 10.00"),
    ("08:10", "BC link alternatif ke jam 12.00"),
    ("09:00", "jowo pools"),
    ("09:10", "TO semua pasaran"),
    ("09:30", "Audit BCA"),
    ("09:45", "First Register"),
    ("10:00", "BC maintenance done (kamis)"),
    ("10:00", "cek data selisih"),
    ("10:00", "total depo"),
    ("10:30", "isi data bola (> jam 1)"),
    ("11:00", "bc maintenance WL (selasa)"),
    ("11:00", "bc jadwal bola"),
    ("12:00", "total depo"),
    ("12:00", "slot & rng mingguan"),
    ("12:30", "cek phising"),
    ("12:50", "live ttm"),
    ("13:00", "wd report"),
    ("13:00", "BC Result Toto Macau"),
    ("13:30", "slot & rng harian"),
    ("14:00", "BC Result Sydney"),
    ("14:00", "depo harian"),
]

# Jadwal Siang
JADWAL_SIANG = [
    ("15:30", "cek link"),
    ("16:00", "cek phising"),
    ("16:00", "deposit harian"),
    ("16:00", "isi data selisih"),
    ("16:00", "BC Result Toto Macau"),
    ("16:30", "jadwalkan bukti jp ke jam 17.00"),
    ("17:40", "SLOT harian (kalau tidak ada sgp jam 18.30)"),
    ("17:50", "BC Result Singapore"),
    ("18:00", "5 lucky ball"),
    ("18:00", "deposit harian"),
    ("18:05", "BC link alt ke jam 19.00"),
    ("18:10", "isi data wlb2c"),
    ("19:00", "BC Result Toto Macau"),
    ("19:30", "Audit BCA"),
    ("19:45", "First Register"),
    ("20:00", "deposit harian"),
    ("21:00", "jowo pools"),
    ("21:00", "cek phising"),
    ("21:00", "wd report"),
    ("22:00", "BC Result Toto Macau"),
    ("22:00", "deposit harian"),
    ("22:45", "Slot harian"),
]

# Jadwal Malam
JADWAL_MALAM = [
    ("23:00", "SLOT harian"),
    ("23:10", "BC Result Hongkong"),
    ("23:30", "cek link & cek phising"),
    ("23:30", "BC rtp slot jam 00.10"),
    ("23:40", "depo harian"),
    ("00:01", "update total bonus"),
    ("00:05", "BC Result Toto Macau"),
    ("00:30", "BC link alt jam 5"),
    ("00:30", "BC bukti JP jam 4"),
    ("00:30", "BC maintenance mingguan ke jam 4 (kamis)"),
    ("00:45", "slot harian"),
    ("01:00", "isi biaya pulsa / isi akuran (senin subuh)"),
    ("01:30", "isi data promo"),
    ("02:00", "total depo"),
    ("02:00", "cek pl config"),
    ("03:30", "Audit BCA"),
    ("03:45", "First Register"),
    ("04:00", "total depo"),
    ("05:00", "cek phising"),
    ("05:00", "wd report"),
    ("05:00", "Slot harian"),
    ("05:45", "total depo"),
]

# Global: aktifkan jadwal apa, default pagi
aktif_jadwal = "pagi"

def parse_time(hhmm: str):
    # Convert "HH:MM" string to time object with TZ
    hh, mm = map(int, hhmm.split(":"))
    return time(hh, mm, tzinfo=TZ)

async def send_jadwal_messages(context: CallbackContext, jadwal_list):
    chat_id = context.job.chat_id
    for jam_str, msg in jadwal_list:
        jam_obj = parse_time(jam_str)
        # Schedule each message for today at jam_obj time
        context.job.scheduler.add_job(
            context.bot.send_message,
            trigger='date',
            run_date=TZ.localize(datetime.combine(datetime.now(TZ).date(), jam_obj)),
            args=[chat_id, f"{jam_str} - {msg}"],
            id=f"{aktif_jadwal}_{jam_str}_{msg}_{chat_id}"
        )
    await context.bot.send_message(chat_id, f"Jadwal {aktif_jadwal} sudah diaktifkan!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard_text = (
        "Pilih jadwal yang ingin diaktifkan:\n"
        "/pagi - Jadwal Pagi\n"
        "/siang - Jadwal Siang\n"
        "/malam - Jadwal Malam\n"
        "/reset - Reset jadwal dan bot untuk hari berikutnya"
    )
    await update.message.reply_text(f"Selamat datang! {keyboard_text}")

async def set_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global aktif_jadwal
    text = update.message.text.lower()
    if "pagi" in text:
        aktif_jadwal = "pagi"
        jadwal_list = JADWAL_PAGI
    elif "siang" in text:
        aktif_jadwal = "siang"
        jadwal_list = JADWAL_SIANG
    elif "malam" in text:
        aktif_jadwal = "malam"
        jadwal_list = JADWAL_MALAM
    else:
        await update.message.reply_text("Pilihan tidak dikenali. Gunakan /pagi, /siang, atau /malam")
        return

    chat_id = update.message.chat_id

    # Cancel existing jobs for this chat first
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()

    # Schedule new jobs
    for jam_str, msg in jadwal_list:
        jam_obj = parse_time(jam_str)
        now = datetime.now(TZ)
        run_dt = datetime.combine(now.date(), jam_obj)
        if run_dt < now:
            run_dt = run_dt.replace(day=now.day + 1)  # next day if time passed
        context.job_queue.run_once(send_single_message, when=run_dt, data=msg, name=str(chat_id))

    await update.message.reply_text(f"Jadwal {aktif_jadwal} sudah diaktifkan!")

async def send_single_message(context: CallbackContext):
    msg = context.job.data
    await context.bot.send_message(context.job.chat_id, msg)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global aktif_jadwal
    aktif_jadwal = "pagi"  # reset ke pagi default
    # Hapus semua job terkait chat ini
    chat_id = update.message.chat_id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("Bot sudah di-reset, siap digunakan lagi untuk hari berikutnya.")

async def webhook_handler(request):
    """Handler webhook POST update dari Telegram."""
    if request.match_info.get("token") != TOKEN:
        return web.Response(status=403)

    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

async def on_startup(app):
    logger.info("Starting webhook server")

async def on_cleanup(app):
    logger.info("Cleaning up webhook server")

if __name__ == "__main__":
    import os
    from datetime import datetime

    TOKEN = os.getenv("TOKEN")
    PORT = int(os.getenv("PORT", 8000))
    WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL_BASE")  # https://yourdomain.com

    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pagi", set_jadwal))
    application.add_handler(CommandHandler("siang", set_jadwal))
    application.add_handler(CommandHandler("malam", set_jadwal))
    application.add_handler(CommandHandler("reset", reset))

    # Webhook setup
    app = web.Application()
    app.router.add_post(f"/{TOKEN}", webhook_handler)

    # Scheduler for daily reset
    scheduler = AsyncIOScheduler(timezone=TZ)
    def daily_reset():
        global aktif_jadwal
        aktif_jadwal = "pagi"
        logger.info("Daily reset executed: aktif_jadwal reset ke pagi")
    scheduler.add_job(daily_reset, "cron", hour=0, minute=0)
    scheduler.start()

    # Run webhook server with aiohttp
    web.run_app(app, port=PORT)
