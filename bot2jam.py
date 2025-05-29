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
user_tasks_done = {}
timezone = pytz.timezone("Asia/Jakarta")

# Jadwal shift sebagai dict waktu: tugas
JADWAL_PAGI = {
    "07:00": "Cek phising",
    "07:05": "Cek link PC Indo & Dana PGA BL",
    "07:15": "Req dana PGA",
    "07:30": "Paito berita",
    "08:00": "Total depo",
    "08:10": "BC link alternatif ke jam 12.00",
    # dst...
}

JADWAL_SIANG = {
    "15:30": "Cek link",
    "16:00": "Cek phising",
    "16:30": "Jadwalkan bukti JP ke jam 17.00",
    "17:50": "BC Result Singapore",
    "18:00": "5 lucky ball",
    # dst...
}

JADWAL_MALAM = {
    "23:00": "Slot harian",
    "23:10": "BC Result Hongkong",
    "23:30": "Cek link & cek phising",
    "00:05": "BC Result Toto Macau",
    # dst...
}

# Kirim pengingat sesuai tugas dan cek apakah sudah selesai
async def reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    thread_id = data.get("thread_id")
    task = data.get("task")

    # Cek apakah task sudah dikerjakan oleh user
    done_tasks = user_tasks_done.get(chat_id, set())
    if task in done_tasks:
        return  # Skip reminder jika sudah selesai

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=f"🔔 {task}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Selesai ✅", callback_data=f"done|{task}")]]
        ),
    )

def schedule_jadwal(chat_id, thread_id, job_queue, jadwal_dict, label, context):
    # Hapus jadwal lama jika ada
    if chat_id in user_jobs:
        for job in user_jobs[chat_id]:
            job.schedule_removal()
        user_jobs.pop(chat_id)

    jobs = []
    for time_str, task in jadwal_dict.items():
        hour, minute = map(int, time_str.split(":"))
        waktu = datetime.time(hour=hour, minute=minute, tzinfo=timezone)

        job = job_queue.run_daily(
            reminder,
            time=waktu,
            chat_id=chat_id,
            name=f"{label}_{time_str}",
            data={"chat_id": chat_id, "thread_id": thread_id, "task": task},
        )
        jobs.append(job)

    user_jobs[chat_id] = jobs
    context.chat_data["reminders"] = [f"{time} - {task}" for time, task in jadwal_dict.items()]
    user_tasks_done[chat_id] = set()

async def start_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE, label: str, jadwal_dict: dict):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id
    schedule_jadwal(chat_id, thread_id, context.job_queue, jadwal_dict, label, context)
    await update.message.reply_text(f"✅ Jadwal *{label.upper()}* telah diaktifkan.\nGunakan /stop untuk menghentikan.")

async def start_pagi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_jadwal(update, context, "pagi", JADWAL_PAGI)

async def start_siang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_jadwal(update, context, "siang", JADWAL_SIANG)

async def start_malam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_jadwal(update, context, "malam", JADWAL_MALAM)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_jobs:
        for job in user_jobs[chat_id]:
            job.schedule_removal()
        user_jobs.pop(chat_id)
    user_tasks_done.pop(chat_id, None)
    context.chat_data.clear()
    await update.message.reply_text("🛑 Semua pengingat dihentikan.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    data = query.data
    if data.startswith("done|"):
        task_done = data.split("|", 1)[1]
        done_set = user_tasks_done.setdefault(chat_id, set())
        if task_done not in done_set:
            done_set.add(task_done)
        # Edit pesan agar tunjukkan sudah selesai
        text = query.message.text_markdown_v2
        new_text = text.replace(task_done, f"~~{task_done}~~ ✅")
        await query.edit_message_text(new_text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Gunakan /startPagi, /startSiang, atau /startMalam untuk memulai jadwal.\n"
        "Gunakan /stop untuk menghentikan semua pengingat.\n"
        "Tiap pengingat akan muncul dengan tombol untuk tandai selesai."
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("❗ Exception occurred:", exc_info=context.error)
    if hasattr(update, "effective_chat") and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, text="⚠️ Terjadi kesalahan. Silakan coba lagi nanti.")
        except Exception:
            pass

async def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("startPagi", start_pagi))
    application.add_handler(CommandHandler("startSiang", start_siang))
    application.add_handler(CommandHandler("startMalam", start_malam))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    # Setup aiohttp server & webhook
    app = web.Application()
    app["application"] = application

    async def handle_root(request):
        return web.Response(text="Bot is running")

    async def handle_webhook(request):
        app = request.app["application"]
        update = await request.json()
        from telegram import Update as TgUpdate
        tg_update = TgUpdate.de_json(update, app.bot)
        await app.update_queue.put(tg_update)
        return web.Response()

    app.add_routes([
        web.get("/", handle_root),
        web.post(WEBHOOK_PATH, handle_webhook),
    ])

    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")
    else:
        logging.warning("WEBHOOK_URL_BASE environment variable not set, webhook disabled!")

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Webserver started on port {port}")

    await application.initialize()
    await application.start()

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
