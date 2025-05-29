import os
import logging
import asyncio
from aiohttp import web
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
PORT = int(os.getenv("PORT", "8000"))
WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL_BASE")
WEBHOOK_URL_PATH = f"/{TOKEN}"
TZ = pytz.timezone(os.getenv("TZ", "Asia/Jakarta"))

# Jadwal lengkap sesuai yang kamu kirim (format "HH:MM", "Kegiatan")
jadwal_pagi = [
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
    ("10:00", "BC maintenance done ( kamis )"),
    ("10:00", "cek data selisih"),
    ("10:00", "total depo"),
    ("10:30", "isi data bola ( > jam 1 )"),
    ("11:00", "bc maintenance WL ( selasa )"),
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

jadwal_siang = [
    ("15:30", "cek link"),
    ("16:00", "cek phising"),
    ("16:00", "deposit harian"),
    ("16:00", "isi data selisih"),
    ("16:00", "BC Result Toto Macau"),
    ("16:30", "jadwalkan bukti jp ke jam 17.00"),
    ("17:40", "SLOT harian ( kalau tifak ada sgp jam 18.30 )"),
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

jadwal_malam = [
    ("23:00", "SLOT harian"),
    ("23:10", "BC Result Hongkong"),
    ("23:30", "cek link & cek phising"),
    ("23:30", "BC rtp slot jam 00.10"),
    ("23:40", "depo harian"),
    ("00:01", "update total bonus"),
    ("00:05", "BC Result Toto Macau"),
    ("00:30", "BC link alt jam 5"),
    ("00:30", "BC bukti JP jam 4"),
    ("00:30", "BC maintenance mingguan ke jam 4 ( kamis )"),
    ("00:45", "slot harian"),
    ("01:00", "isi biaya pulsa / isi akuran ( senin subuh )"),
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

active_schedule = None
user_chat_id = None  # Simpel, simpan chat_id pengguna yang pilih jadwal, buat kirim pesan


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_chat_id
    user_chat_id = update.effective_chat.id

    keyboard = [["pagi", "siang", "malam"], ["reset"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Halo! Silakan pilih jadwal yang ingin diaktifkan:\n(pagi / siang / malam)\nAtau ketik 'reset' untuk reset bot.",
        reply_markup=reply_markup
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_schedule, user_chat_id
    user_chat_id = update.effective_chat.id
    text = update.message.text.lower()

    if text == "reset":
        active_schedule = None
        await update.message.reply_text("Bot sudah di-reset. Silakan pilih jadwal lagi dengan /start.")
        return

    if text in ("pagi", "siang", "malam"):
        active_schedule = text
        await update.message.reply_text(f"Jadwal '{text}' telah diaktifkan.")
    else:
        await update.message.reply_text("Pilihan tidak valid. Ketik /start untuk memilih jadwal.")


async def cek_jadwal(context: ContextTypes.DEFAULT_TYPE):
    if not active_schedule or not user_chat_id:
        return  # Tidak ada jadwal aktif / chat id

    now = datetime.now(TZ).strftime("%H:%M")
    jadwal = None

    if active_schedule == "pagi":
        jadwal = jadwal_pagi
    elif active_schedule == "siang":
        jadwal = jadwal_siang
    elif active_schedule == "malam":
        jadwal = jadwal_malam

    if not jadwal:
        return

    for jam, kegiatan in jadwal:
        if jam == now:
            try:
                await context.bot.send_message(chat_id=user_chat_id, text=f"🕒 {jam} - {kegiatan}")
            except Exception as e:
                logger.error(f"Error kirim pesan: {e}")


async def webhook_handler(request: web.Request):
    """Terima update dari Telegram via webhook."""
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return web.Response(text="ok")


async def on_startup(app):
    await application.bot.set_webhook(WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
    logger.info(f"Webhook set at {WEBHOOK_URL_BASE + WEBHOOK_URL_PATH}")


async def main():
    global application
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Job queue cek jadwal tiap menit
    job_queue = application.job_queue
    job_queue.run_repeating(cek_jadwal, interval=60, first=10)

    # Setup aiohttp webserver untuk webhook
    app = web.Application()
    app.router.add_post(WEBHOOK_URL_PATH, webhook_handler)
    app.on_startup.append(on_startup)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"Server started on port {PORT}")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
