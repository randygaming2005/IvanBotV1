import logging
import os
import datetime
import pytz
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
)

TOKEN = os.environ.get("BOT_TOKEN", "8166249822:AAFcdKH1fEoEMkEGTmfuw71NbvwMmh4rGaI")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://ivanbotv1.onrender.com/{TOKEN}"
PORT = int(os.environ.get('PORT', 8000))

# Set logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Selamat datang! Gunakan /set HH:MM untuk atur pengingat harian.")


async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⛔️ Format: /set HH:MM")
        return

    try:
        waktu = context.args[0]
        jam, menit = map(int, waktu.split(":"))

        if not (0 <= jam < 24 and 0 <= menit < 60):
            raise ValueError

        tz = pytz.timezone("Asia/Jakarta")
        now = datetime.datetime.now(tz)
        target = now.replace(hour=jam, minute=menit, second=0, microsecond=0)

        if target <= now:
            target += datetime.timedelta(days=1)

        delta = (target - now).total_seconds()

        job_queue = context.job_queue
        if job_queue is None:
            raise Exception("JobQueue tidak tersedia!")

        async def send_reminder(ctx: ContextTypes.DEFAULT_TYPE):
            await ctx.bot.send_message(chat_id=update.effective_chat.id, text="⏰ Waktunya sekarang!")

        job_queue.run_once(send_reminder, delta)

        await update.message.reply_text(f"✅ Pengingat disetel pukul {waktu} (WIB)")
    except Exception as e:
        logger.error(f"Error set reminder: {e}")
        await update.message.reply_text(f"⛔️ Format waktu tidak valid: {context.args[0]}")


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        job_queue = context.job_queue
        if job_queue is None:
            raise Exception("JobQueue tidak tersedia!")

        async def test_job(ctx: ContextTypes.DEFAULT_TYPE):
            await ctx.bot.send_message(chat_id=update.effective_chat.id, text="🧪 Reminder test jalan!")

        job_queue.run_once(test_job, 5)
        await update.message.reply_text("🕔 Reminder test akan dikirim dalam 5 detik.")
    except Exception as e:
        logger.error(f"Gagal test reminder: {e}")
        await update.message.reply_text("⚠️ Gagal menjadwalkan reminder.")


async def webhook_handler(request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.update_queue.put(update)
    return web.Response(text="ok")


async def on_startup(app):
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"🌐 Webhook set to {WEBHOOK_URL}")


if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()
    bot = application.bot

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set", set_reminder))
    application.add_handler(CommandHandler("test", test))

    # Webhook server
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, webhook_handler)
    app.on_startup.append(on_startup)

    logger.info(f"🚀 Server berjalan di port {PORT}")
    web.run_app(app, port=PORT)
