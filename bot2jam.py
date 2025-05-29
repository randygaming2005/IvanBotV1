import logging
import os
import datetime
import pytz
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, PicklePersistence, JobQueue
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN") or "YOUR_BOT_TOKEN_HERE"
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None
PORT = int(os.environ.get("PORT", 8000))

timezone = pytz.timezone("Asia/Jakarta")
persistence = PicklePersistence(filepath="data.pkl")

# Jadwal lengkap per sesi
JADWAL_PAGI = [
    "07:00 cek phising", "07:05 cek link pc indo", "07:05 cek dana PGA BL", "07:15 req dana PGA",
    "07:30 paito berita", "08:00 total depo", "08:00 Slot Harian", "08:00 jadwalkan bukti jp ke jam 10.00",
    "08:10 BC link alternatif ke jam 12.00", "09:00 jowo pools", "09:10 TO semua pasaran",
    "09:30 Audit BCA", "09:45 First Register", "10:00 BC maintenance done ( kamis )", "10:00 cek data selisih",
    "10:00 total depo", "10:30 isi data bola ( > jam 1 )", "11:00 bc maintenance WL ( selasa )",
    "11:00 bc jadwal bola", "12:00 total depo", "12:00 slot & rng mingguan", "12:30 cek phising",
    "12:50 live ttm", "13:00 wd report", "13:00 BC Result Toto Macau", "13:30 slot & rng harian",
    "14:00 BC Result Sydney", "14:00 depo harian"
]

JADWAL_SIANG = [
    "15:30 cek link", "16:00 cek phising", "16:00 deposit harian", "16:00 isi data selisih",
    "16:00 BC Result Toto Macau", "16:30 jadwalkan bukti jp ke jam 17.00",
    "17:40 SLOT harian ( kalau tifak ada sgp jam 18.30 )", "17:50 BC Result Singapore",
    "18:00 5 lucky ball", "18:00 deposit harian", "18:05 BC link alt ke jam 19.00",
    "18:10 isi data wlb2c", "19:00 BC Result Toto Macau", "19:30 Audit BCA", "19:45 First Register",
    "20:00 deposit harian", "21:00 jowo pools", "21:00 cek phising", "21:00 wd report",
    "22:00 BC Result Toto Macau", "22:00 deposit harian", "22:45 Slot harian"
]

JADWAL_MALAM = [
    "23:00 SLOT harian", "23:10 BC Result Hongkong", "23:30 cek link & cek phising",
    "23:30 BC rtp slot jam 00.10", "23:40 depo harian", "00:01 update total bonus",
    "00:05 BC Result Toto Macau", "00:30 BC link alt jam 5", "00:30 BC bukti JP jam 4",
    "00:30 BC maintenance mingguan ke jam 4 ( kamis )", "00:45 slot harian",
    "01:00 isi biaya pulsa / isi akuran ( senin subuh )", "01:30 isi data promo",
    "02:00 total depo", "02:00 cek pl config", "03:30 Audit BCA", "03:45 First Register",
    "04:00 total depo", "05:00 cek phising", "05:00 wd report", "05:00 Slot harian",
    "05:45 total depo"
]

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("JADWAL PAGI", callback_data="jadwal_pagi")],
        [InlineKeyboardButton("JADWAL SIANG", callback_data="jadwal_siang")],
        [InlineKeyboardButton("JADWAL MALAM", callback_data="jadwal_malam")],
    ])

def jadwal_keyboard(jadwal_list, done_set):
    buttons = [
        [InlineKeyboardButton(f"{'✅' if idx in done_set else '⬜'} {item}", callback_data=f"toggle_done:{idx}")]
        for idx, item in enumerate(jadwal_list)
    ]
    # Tambahkan tombol kembali
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Silakan pilih jadwal yang ingin dilihat:", reply_markup=main_menu_keyboard())

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reset semua done sets dalam chat_data untuk grup itu
    context.chat_data["done_pagi"] = set()
    context.chat_data["done_siang"] = set()
    context.chat_data["done_malam"] = set()
    await update.message.reply_text("✅ Semua tugas telah direset. Siap digunakan kembali besok!")

async def waktu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(timezone)
    await update.message.reply_text(f"Waktu server sekarang:\n{now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

def format_jadwal(jadwal_list, done_set):
    return "\n".join([
        f"{'✅' if idx in done_set else '⬜'} {item}" for idx, item in enumerate(jadwal_list)
    ])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_data = context.chat_data
    data = query.data

    if data == "back_to_menu":
        await query.edit_message_text("Silakan pilih jadwal yang ingin dilihat:", reply_markup=main_menu_keyboard())
        return

    if data.startswith("jadwal_"):
        current = data.split("_")[1]
        chat_data["current_jadwal"] = current
        jadwal_map = {"pagi": JADWAL_PAGI, "siang": JADWAL_SIANG, "malam": JADWAL_MALAM}
        done_set = chat_data.setdefault(f"done_{current}", set())
        await query.edit_message_text(
            f"JADWAL {current.upper()}:\n\n" + format_jadwal(jadwal_map[current], done_set),
            reply_markup=jadwal_keyboard(jadwal_map[current], done_set),
        )
        return

    if data.startswith("toggle_done:"):
        idx = int(data.split(":")[1])
        current = chat_data.get("current_jadwal")
        if not current:
            await query.answer("Pilih jadwal dulu.", show_alert=True)
            return

        key = f"done_{current}"
        done_set = chat_data.setdefault(key, set())
        if idx in done_set:
            done_set.remove(idx)
        else:
            done_set.add(idx)

        jadwal_map = {"pagi": JADWAL_PAGI, "siang": JADWAL_SIANG, "malam": JADWAL_MALAM}
        await query.edit_message_text(
            f"JADWAL {current.upper()}:\n\n" + format_jadwal(jadwal_map[current], done_set),
            reply_markup=jadwal_keyboard(jadwal_map[current], done_set),
        )

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    jadwal_list = job.data.get("jadwal_list")
    item_idx = job.data.get("item_idx")
    item_text = jadwal_list[item_idx]

    # Kirim pengingat ke grup
    try:
        await context.bot.send_message(chat_id, f"⏰ Pengingat: Tugas '{item_text}' akan dimulai dalam 5 menit!")
    except Exception as e:
        logger.error(f"Gagal mengirim pengingat ke chat {chat_id}: {e}")

def parse_time_from_task(task_text):
    # Contoh task_text "07:00 cek phising"
    # Ambil jam dan menit
    time_str = task_text.split()[0]
    try:
        hh, mm = time_str.split(":")
        return int(hh), int(mm)
    except Exception as e:
        logger.warning(f"Error parsing waktu dari task '{task_text}': {e}")
        return None, None

async def schedule_reminders(application):
    # Fungsi ini akan scheduling job untuk semua jadwal pagi, siang, malam di chat yang pakai bot
    # Job tiap item dijadwalkan 5 menit sebelum waktu yang tercantum di string jadwal
    # Kirim pengingat 5 menit sebelum

    # Ambil semua chat_id yang pernah pakai bot (ada di persistence)
    all_chats = list(application.persistence.chat_data.keys())
    jadwal_map = {
        "pagi": JADWAL_PAGI,
        "siang": JADWAL_SIANG,
        "malam": JADWAL_MALAM,
    }

    for chat_id in all_chats:
        for jadwal_key, jadwal_list in jadwal_map.items():
            for idx, item in enumerate(jadwal_list):
                hh, mm = parse_time_from_task(item)
                if hh is None or mm is None:
                    continue

                # Waktu pengingat = waktu tugas - 5 menit
                reminder_time = datetime.datetime.now(timezone).replace(hour=hh, minute=mm, second=0, microsecond=0) - datetime.timedelta(minutes=5)
                now = datetime.datetime.now(timezone)
                if reminder_time < now:
                    # Jika sudah lewat hari ini, schedule untuk besok
                    reminder_time += datetime.timedelta(days=1)

                # Convert ke UTC untuk job queue
                reminder_time_utc = reminder_time.astimezone(pytz.utc)

                # Cek kalau sudah ada job dengan id sama, skip
                job_name = f"reminder_{chat_id}_{jadwal_key}_{idx}"
                existing_jobs = application.job_queue.get_jobs_by_name(job_name)
                if existing_jobs:
                    continue

                application.job_queue.run_once(send_reminder, reminder_time_utc, chat_id=chat_id, data={"jadwal_list": jadwal_list, "item_idx": idx}, name=job_name)
                logger.info(f"Scheduled reminder for chat {chat_id} task '{item}' at {reminder_time_utc.isoformat()} UTC")

async def on_startup(application):
    # Run saat bot start, schedule reminder
    await schedule_reminders(application)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception occurred:", exc_info=context.error)
    if hasattr(update, "effective_chat") and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, text="⚠️ Terjadi kesalahan. Silakan coba lagi nanti.")
        except Exception:
            pass

# Webhook handler
async def handle_root(request):
    return web.Response(text="Bot is running")

async def handle_webhook(request):
    application = request.app["application"]
    update_json = await request.json()
    from telegram import Update as TgUpdate
    update = TgUpdate.de_json(update_json, application.bot)
    await application.update_queue.put(update)
    return web.Response()

async def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("waktu", waktu))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    # Web server routes
    app = web.Application()
    app["application"] = application
    app.add_routes([
        web.get("/", handle_root),
        web.post(WEBHOOK_PATH, handle_webhook),
    ])

    # Set webhook if URL provided
    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    else:
        logger.warning("WEBHOOK_URL_BASE not set, webhook disabled!")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Webserver started on port {PORT}")

    # Start bot & schedule reminders on startup
    await application.initialize()
    await application.start()
    await on_startup(application)

    # Run forever
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
