import logging
import os
import datetime
import pytz
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler,
    PicklePersistence, JobQueue
)

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment
PORT = int(os.environ.get("PORT", 8000))
TOKEN = os.environ.get("TOKEN")
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None
timezone = pytz.timezone("Asia/Jakarta")
persistence = PicklePersistence(filepath="data.pkl")

JADWAL = {
    "pagi": [...],  # masukkan semua dari list pagi
    "siang": [...],  # dari list siang
    "malam": [...]  # dari list malam
}

# Masukkan jadwal kamu seperti yang sudah kamu kirim ke dalam masing-masing list

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Jadwal Pagi", callback_data="jadwal_pagi")],
        [InlineKeyboardButton("🟡 Jadwal Siang", callback_data="jadwal_siang")],
        [InlineKeyboardButton("🔵 Jadwal Malam", callback_data="jadwal_malam")],
    ])

def jadwal_keyboard(session, selected, done):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'✅' if i in done else '⬜'} {t}", callback_data=f"toggle:{session}:{i}")]
        for i, t in enumerate(selected)
    ] + [[InlineKeyboardButton("🔙 Kembali", callback_data="back")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pilih jadwal untuk ditampilkan:", reply_markup=main_menu())

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for s in JADWAL.keys():
        context.chat_data[f"done_{s}"] = set()
    await update.message.reply_text("✅ Semua status tugas telah direset.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        await query.edit_message_text("Pilih jadwal untuk ditampilkan:", reply_markup=main_menu())
    elif data.startswith("jadwal_"):
        session = data.split("_")[1]
        context.chat_data["current"] = session
        selected = JADWAL[session]
        done = context.chat_data.setdefault(f"done_{session}", set())
        await query.edit_message_text(
            f"JADWAL {session.upper()}:\n\n" + "\n".join(
                f"{'✅' if i in done else '⬜'} {task}" for i, task in enumerate(selected)
            ), reply_markup=jadwal_keyboard(session, selected, done)
        )
    elif data.startswith("toggle:"):
        _, session, idx = data.split(":")
        idx = int(idx)
        done = context.chat_data.setdefault(f"done_{session}", set())
        done.remove(idx) if idx in done else done.add(idx)
        selected = JADWAL[session]
        await query.edit_message_text(
            f"JADWAL {session.upper()}:\n\n" + "\n".join(
                f"{'✅' if i in done else '⬜'} {task}" for i, task in enumerate(selected)
            ), reply_markup=jadwal_keyboard(session, selected, done)
        )

def parse_time(task):
    try:
        jam = task.split()[0].replace(".", ":")
        hh, mm = map(int, jam.split(":"))
        return hh, mm
    except:
        return None, None

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    text = job.data["text"]
    try:
        await context.bot.send_message(chat_id, f"⏰ Pengingat: '{text}' akan dimulai 5 menit lagi!")
    except Exception as e:
        logger.warning(f"❌ Gagal kirim ke {chat_id}: {e}")

async def schedule_jobs(app):
    for chat_id in app.persistence.chat_data.keys():
        for sesi, daftar in JADWAL.items():
            for i, task in enumerate(daftar):
                hh, mm = parse_time(task)
                if hh is None: continue
                waktu = datetime.datetime.now(timezone).replace(hour=hh, minute=mm, second=0, microsecond=0)
                if waktu < datetime.datetime.now(timezone):
                    waktu += datetime.timedelta(days=1)
                waktu -= datetime.timedelta(minutes=5)
                utc_time = waktu.astimezone(pytz.utc)
                job_id = f"{chat_id}_{sesi}_{i}"
                if not app.job_queue.get_jobs_by_name(job_id):
                    app.job_queue.run_once(send_reminder, utc_time, chat_id=chat_id, data={"text": task}, name=job_id)

async def handle_root(request):
    return web.Response(text="Bot aktif")

async def handle_webhook(request):
    app = request.app["application"]
    update_json = await request.json()
    update = Update.de_json(update_json, app.bot)
    await app.update_queue.put(update)
    return web.Response()

async def main():
    app = ApplicationBuilder().token(TOKEN).persistence(persistence).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(button_handler))

    web_app = web.Application()
    web_app["application"] = app
    web_app.add_routes([
        web.get("/", handle_root),
        web.post(WEBHOOK_PATH, handle_webhook),
    ])

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    await app.bot.set_webhook(WEBHOOK_URL)
    await app.initialize()
    await app.start()
    await schedule_jobs(app)

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
