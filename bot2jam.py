import logging
import os
from aiohttp import web
from datetime import datetime, time, timedelta
import pytz

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ApplicationBuilder,
)

TOKEN = os.getenv("BOT_TOKEN") or "8166249822:AAFcdKH1fEoEMkEGTmfuw71NbvwMmh4rGaI"
WEBHOOK_URL = f"https://ivanbotv1.onrender.com/{TOKEN}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone Indonesia
TZ = pytz.timezone("Asia/Jakarta")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirim /set HH:MM untuk reminder.")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.job_queue:
            when = datetime.now(TZ) + timedelta(seconds=10)
            context.job_queue.run_once(test_callback, when, chat_id=update.effective_chat.id)
            await update.message.reply_text("✅ Test reminder dijadwalkan!")
        else:
            raise ValueError("JobQueue tidak aktif")
    except Exception as e:
        logger.error(f"Gagal test reminder: {e}")
        await update.message.reply_text("⚠️ Gagal menjadwalkan reminder.")

async def test_callback(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=context.job.chat_id, text="⏰ Ini adalah test reminder!")

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("⛔️ Format: /set HH:MM")
            return

        time_str = context.args[0]
        jam, menit = map(int, time_str.split(":"))
        now = datetime.now(TZ)
        target = TZ.localize(datetime.combine(now.date(), time(jam, menit)))
        if target < now:
            target += timedelta(days=1)

        if context.job_queue:
            context.job_queue.run_once(reminder_callback, target, chat_id=update.effective_chat.id)
            await update.message.reply_text(f"⏰ Reminder disetel untuk {target.strftime('%H:%M')}")
        else:
            raise ValueError("JobQueue tidak aktif")
    except Exception as e:
        logger.error(f"❌ Error parsing time {time_str}: {e}")
        await update.message.reply_text(f"⛔️ Format waktu tidak valid: {time_str}")

async def reminder_callback(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=context.job.chat_id, text="🔔 🔔 Woi jam berapa ini ? Kau pikir tugas itu bisa siap sendiri? jangan nanti-nanti kau bilang 'lupa pulak kau nanti 🔔!")

async def webhook(request):
    data = await request.json()
    await app.update_queue.put(data)
    return web.Response()

async def main():
    global app
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set", set_reminder))
    app.add_handler(CommandHandler("test", test))

    # Webhook setup
    await app.bot.set_webhook(WEBHOOK_URL)

    runner = web.AppRunner(web.Application().add_routes([web.post(f"/{TOKEN}", webhook)]))
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()

    logger.info(f"🌐 Webhook set to {WEBHOOK_URL}")
    logger.info("🚀 Server berjalan di port 8000")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()  # Safe alternative to keep it alive
    await app.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
