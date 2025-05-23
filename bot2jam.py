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

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = "8166249822:AAFcdKH1fEoEMkEGTmfuw71NbvwMmh4rGaI"  # Ganti dengan token kamu
persistence = PicklePersistence(filepath="reminder_data.pkl")
user_jobs = {}
timezone = pytz.timezone("Asia/Jakarta")

# --- Telegram Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Gunakan /set jam:menit (contoh: /set 08:30 12:45) untuk pengingat harian.\n"
        "/list untuk cek pengingat, /stop untuk hapus semua, /test untuk uji pengingat 1 menit."
    )

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    logging.info(f"🔔 Menjalankan pengingat untuk chat_id {chat_id}")
    await context.bot.send_message(
        chat_id,
        text="🔔 Woi jam berapa ini? Kau pikir tugas itu bisa siap sendiri? Jangan nanti-nanti kau bilang 'lupa pulak kau nanti' 🔔"
    )

async def set_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_jobs:
        for job in user_jobs[chat_id]:
            job.schedule_removal()
        user_jobs.pop(chat_id)

    args = context.args
    if not args:
        await update.message.reply_text("❌ Format salah! Gunakan: /set 08:30 12:45")
        return

    reminder_times = []
    jobs = []

    for waktu_str in args:
        try:
            hour, minute = map(int, waktu_str.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError("Jam atau menit tidak valid.")

            waktu = datetime.time(hour=hour, minute=minute, tzinfo=timezone)

            job = context.job_queue.run_daily(
                reminder,
                waktu,
                chat_id=chat_id,
                name=f"reminder_{waktu_str}",
                data=chat_id
            )
            jobs.append(job)
            reminder_times.append(waktu_str)
            logging.info(f"✅ Menjadwalkan pengingat {waktu_str} untuk chat_id {chat_id}")

        except Exception as e:
            await update.message.reply_text(f"⛔ Format salah atau waktu tidak valid: {waktu_str}")
            logging.error(f"❌ Error parsing time {waktu_str}: {e}")
            return

    user_jobs[chat_id] = jobs
    context.chat_data["reminders"] = reminder_times
    await update.message.reply_text(f"✅ Pengingat diatur untuk: {', '.join(reminder_times)}")

async def list_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = context.chat_data.get("reminders")
    if not reminders:
        await update.message.reply_text("🚫 Tidak ada pengingat yang aktif.")
    else:
        await update.message.reply_text("📋 Pengingat aktif:\n" + "\n".join(f"- {w}" for w in reminders))

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_jobs:
        await update.message.reply_text("🚫 Tidak ada pengingat yang aktif.")
        return

    for job in user_jobs[chat_id]:
        job.schedule_removal()
    user_jobs.pop(chat_id)
    context.chat_data.clear()
    await update.message.reply_text("🛑 Semua pengingat dihentikan.")

async def test_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        context.job_queue.run_once(
            reminder,
            when=datetime.timedelta(seconds=60),
            chat_id=chat_id,
            name="test_reminder",
            data=chat_id
        )
        await update.message.reply_text("⏳ Pengingat akan dikirim dalam 1 menit.")
    except Exception as e:
        await update.message.reply_text("⚠️ Gagal menjadwalkan pengingat.")
        logging.error(f"Error scheduling test reminder: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("❗ Exception occurred:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, text="⚠️ Terjadi kesalahan. Silakan coba lagi nanti.")
        except Exception:
            pass

# --- Main with webhook ---

async def main():
    WEBHOOK_PATH = f"/{TOKEN}"
    WEBHOOK_URL = f"https://ivanbotv1.onrender.com{WEBHOOK_PATH}"  # Ganti dengan domain kamu

    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence)
        .post_init(lambda app: logging.info("✅ Bot siap berjalan dengan JobQueue aktif..."))
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set", set_times))
    application.add_handler(CommandHandler("list", list_times))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("test", test_reminder))
    application.add_error_handler(error_handler)

    # Set webhook Telegram ke URL kamu
    await application.bot.set_webhook(WEBHOOK_URL)
    logging.info(f"🌐 Webhook set ke {WEBHOOK_URL}")

    # Buat dan jalankan aiohttp server untuk menerima webhook dari Telegram
    app = application.create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8000)))
    await site.start()

    logging.info(f"🌐 Webserver dan bot siap menerima webhook di port {os.environ.get('PORT', 8000)}")

    # Jangan keluar dari main agar server terus jalan
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())