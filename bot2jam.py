import logging
import datetime
import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Env config
TOKEN = os.environ.get("TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None
PORT = int(os.environ.get("PORT", 8000))

# In-memory storage
user_jobs = {}

# === Command Handlers ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Gunakan /set jam:menit (contoh: /set 08:30 12:45) untuk pengingat harian.\n"
        "/list untuk cek pengingat, /stop untuk hapus semua, /test untuk uji pengingat 1 menit."
    )

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    logging.info(f"🔔 Reminder dijalankan untuk chat_id {chat_id}")
    await context.bot.send_message(chat_id, "🔔 Woi jam berapa ini ? Kau pikir tugas itu bisa siap sendiri? jangan nanti-nanti kau bilang 'lupa pulak kau nanti 🔔!")

async def set_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    if not args:
        await update.message.reply_text("❌ Format salah! Gunakan: /set 08:30 12:45")
        return

    if chat_id in user_jobs:
        for job in user_jobs[chat_id]:
            job.schedule_removal()
        user_jobs.pop(chat_id)

    jobs = []
    reminder_times = []

    for time_str in args:
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
            waktu = datetime.time(hour=hour, minute=minute)
            job = context.job_queue.run_daily(
                reminder,
                time=waktu,
                chat_id=chat_id,
                name=f"reminder_{time_str}",
                data=chat_id
            )
            jobs.append(job)
            reminder_times.append(time_str)
        except:
            await update.message.reply_text(f"⛔ Format waktu tidak valid: {time_str}")
            return

    user_jobs[chat_id] = jobs
    context.chat_data["reminders"] = reminder_times
    await update.message.reply_text(f"✅ Reminder diatur untuk: {', '.join(reminder_times)}")

async def list_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = context.chat_data.get("reminders", [])
    if not reminders:
        await update.message.reply_text("🚫 Tidak ada reminder aktif.")
    else:
        await update.message.reply_text("📋 Reminder aktif:\n" + "\n".join(f"- {w}" for w in reminders))

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_jobs:
        await update.message.reply_text("🚫 Tidak ada reminder untuk dihentikan.")
        return
    for job in user_jobs[chat_id]:
        job.schedule_removal()
    user_jobs.pop(chat_id)
    context.chat_data.clear()
    await update.message.reply_text("🛑 Semua reminder dihentikan.")

async def test_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        context.job_queue.run_once(
            reminder,
            when=60,
            chat_id=chat_id,
            name="test_reminder",
            data=chat_id
        )
        await update.message.reply_text("⏳ Reminder test akan dikirim dalam 1 menit.")
    except Exception as e:
        logging.error(f"Gagal test reminder: {e}")
        await update.message.reply_text("⚠️ Gagal menjadwalkan reminder.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("❗ Exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(update.effective_chat.id, "⚠️ Terjadi kesalahan.")

# === Webhook & Server ===

async def handle_root(request):
    return web.Response(text="Bot is running")

async def handle_webhook(request):
    app = request.app["application"]
    data = await request.json()
    from telegram import Update as TgUpdate
    tg_update = TgUpdate.de_json(data, app.bot)
    await app.update_queue.put(tg_update)
    return web.Response()

async def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set", set_times))
    application.add_handler(CommandHandler("list", list_times))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("test", test_reminder))
    application.add_error_handler(error_handler)

    # aiohttp web server
    app = web.Application()
    app["application"] = application
    app.add_routes([
        web.get("/", handle_root),
        web.post(WEBHOOK_PATH, handle_webhook),
    ])

    # Webhook ke Telegram
    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        logging.info(f"🌐 Webhook set to {WEBHOOK_URL}")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"🚀 Server berjalan di port {PORT}")

    await application.initialize()
    await application.start()
    await application.running.wait_closed()  # keep alive

if __name__ == "__main__":
    asyncio.run(main())
