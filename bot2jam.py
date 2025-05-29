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

# Konfigurasi logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Token dan URL Webhook dari environment variable
TOKEN = os.environ.get("TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None

# Persistence untuk menyimpan data
persistence = PicklePersistence(filepath="reminder_data.pkl")

# Variabel global
user_jobs = {}
user_tasks_done = {}
timezone = pytz.timezone("Asia/Jakarta")

# Jadwal lengkap
JADWAL_PAGI = {
    "07:00": "Cek phising",
    "07:05": "Cek link PC Indo",
    "07:05": "Cek dana PGA BL",
    "07:15": "Req dana PGA",
    "07:30": "Paito berita",
    "08:00": "Total depo",
    "08:00": "Slot Harian",
    "08:00": "Jadwalkan bukti JP ke jam 10.00",
    "08:10": "BC link alternatif ke jam 12.00",
    "09:00": "Jowo pools",
    "09:10": "TO semua pasaran",
    "09:30": "Audit BCA",
    "09:45": "First Register",
    "10:00": "BC maintenance done (Kamis)",
    "10:00": "Cek data selisih",
    "10:00": "Total depo",
    "10:30": "Isi data bola (> jam 1)",
    "11:00": "BC maintenance WL (Selasa)",
    "11:00": "BC jadwal bola",
    "12:00": "Total depo",
    "12:00": "Slot & RNG mingguan",
    "12:50": "Live TTM",
    "12:30": "Cek phising",
    "13:00": "WD report",
    "13:00": "BC Result Toto Macau",
    "13:30": "Slot & RNG harian",
    "14:00": "BC Result Sydney",
    "14:00": "Depo harian",
}

JADWAL_SIANG = {
    "15:30": "Cek link",
    "16:00": "Cek phising",
    "16:00": "Deposit harian",
    "16:00": "Isi data selisih",
    "16:00": "BC Result Toto Macau",
    "16:30": "Jadwalkan bukti JP ke jam 17.00",
    "17:40": "Slot harian (kalau tidak ada SGP jam 18.30)",
    "17:50": "BC Result Singapore",
    "18:00": "5 Lucky Ball",
    "18:00": "Deposit harian",
    "18:05": "BC link alt ke jam 19.00",
    "18:10": "Isi data WLB2C",
    "19:00": "BC Result Toto Macau",
    "19:30": "Audit BCA",
    "19:45": "First Register",
    "20:00": "Deposit harian",
    "21:00": "Jowo pools",
    "21:00": "Cek phising",
    "21:00": "WD report",
    "22:00": "BC Result Toto Macau",
    "22:00": "Deposit harian",
    "22:45": "Slot harian",
}

JADWAL_MALAM = {
    "23:00": "Slot harian",
    "23:10": "BC Result Hongkong",
    "23:30": "Cek link & cek phising",
    "23:30": "BC RTP slot jam 00.10",
    "23:40": "Depo harian",
    "00:01": "Update total bonus",
    "00:05": "BC Result Toto Macau",
    "00:30": "BC link alt jam 5",
    "00:30": "BC bukti JP jam 4",
    "00:30": "BC maintenance mingguan ke jam 4 (Kamis)",
    "00:45": "Slot harian",
    "01:00": "Isi biaya pulsa / akuran (Senin subuh)",
    "01:30": "Isi data promo",
    "02:00": "Total depo",
    "02:00": "Cek PL config",
    "03:30": "Audit BCA",
    "03:45": "First Register",
    "04:00": "Total depo",
    "05:00": "Cek phising",
    "05:00": "WD report",
    "05:00": "Slot harian",
    "05:45": "Total depo",
}

# Fungsi reminder
async def reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    thread_id = data.get("thread_id")
    task = data.get("task")

    if task in user_tasks_done.get(chat_id, set()):
        return

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=f"🔔 {task}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Selesai ✅", callback_data=f"done|{task}")]]
        ),
    )

# Penjadwalan
def schedule_jadwal(chat_id, thread_id, job_queue, jadwal_dict, label, context):
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

# Command handler
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

# Handler tombol "Selesai"
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    if data.startswith("done|"):
        task_done = data.split("|", 1)[1]
        user_tasks_done.setdefault(chat_id, set()).add(task_done)
        text = query.message.text_markdown_v2
        new_text = text.replace(task_done, f"~~{task_done}~~ ✅")
        await query.edit_message_text(new_text)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Gunakan perintah berikut:\n"
        "🕐 /startPagi\n"
        "🕐 /startSiang\n"
        "🕐 /startMalam\n"
        "🛑 /stop untuk menghentikan semua pengingat."
    )

# Handler error
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("❗ Exception occurred:", exc_info=context.error)

# Fungsi utama
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

    app = web.Application()
    app["application"] = application

    async def handle_root(request):
        return web.Response(text="Bot is running")

    async def handle_webhook(request):
        update = await request.json()
        from telegram import Update as TgUpdate
        tg_update = TgUpdate.de_json(update, application.bot)
        await application.update_queue.put(tg_update)
        return web.Response()

    app.add_routes([
        web.get("/", handle_root),
        web.post(WEBHOOK_PATH, handle_webhook),
    ])

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Webserver started on port {port}")

    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

# Jalankan program
if __name__ == "__main__":
    asyncio.run(main())
