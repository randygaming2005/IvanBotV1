import logging
import os
import datetime
import pytz
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, PicklePersistence
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None
PORT = int(os.environ.get("PORT", 8000))
TIMEZONE = pytz.timezone(os.environ.get("TZ", "Asia/Jakarta"))

persistence = PicklePersistence(filepath="data.pkl")

# --- Jadwal yang kamu kirim ---
JADWAL_PAGI = [
    "07:05 cek link pc indo", "07:00 cek phising", "07:05 cek dana PGA BL", "07:15 req dana PGA",
    "07:30 paito berita", "08:00 total depo", "08:00 Slot Harian", "08:00 jadwalkan bukti jp ke jam 10.00",
    "08:10 BC link alternatif ke jam 12.00", "09:00 jowo pools", "09:10 TO semua pasaran",
    "09:30 Audit BCA", "09:45 First Register", "10:00 BC maintenance done ( kamis )",
    "10:00 cek data selisih", "10:00 total depo", "10:30 isi data bola ( > jam 1 )",
    "11:00 bc maintenance WL ( selasa )", "11:00 bc jadwal bola", "12:00 total depo",
    "12:00 slot & rng mingguan", "12:50 live ttm", "12:30 cek phising", "13:00 wd report",
    "13:00 BC Result Toto Macau", "13:30 slot & rng harian", "14:00 BC Result Sydney", "14:00 depo harian"
]

JADWAL_SIANG = [
    "15:30 cek link", "16:00 cek phising", "16:00 deposit harian", "16:30 jadwalkan bukti jp ke jam 17.00",
    "16:00 isi data selisih", "16:00 BC Result Toto Macau", "17:40 SLOT harian ( kalau tifak ada sgp jam 18.30 )",
    "17:50 BC Result Singapore", "18:00 5 lucky ball", "18:00 deposit harian", "18:05 BC link alt ke jam 19.00",
    "18:10 isi data wlb2c", "19:00 BC Result Toto Macau", "19:30 Audit BCA", "19:45 First Register",
    "20:00 deposit harian", "21:00 jowo pools", "21:00 cek phising", "21:00 wd report",
    "22:00 BC Result Toto Macau", "22:00 deposit harian", "22:45 Slot harian"
]

JADWAL_MALAM = [
    "23:00 SLOT harian", "23:10 BC Result Hongkong", "23:30 cek link & cek phising", "23:30 BC rtp slot jam 00.10",
    "23:40 depo harian", "00:05 BC Result Toto Macau", "00:01 update total bonus", "00:30 BC link alt jam 5",
    "00:30 BC bukti JP jam 4", "00:30 BC maintenance mingguan ke jam 4 ( kamis )", "00:45 slot harian",
    "01:00 isi biaya pulsa / isi akuran ( senin subuh )", "01:30 isi data promo", "02:00 total depo",
    "02:00 cek pl config", "03:30 Audit BCA", "03:45 First Register", "04:00 total depo", "05:00 cek phising",
    "05:00 wd report", "05:00 Slot harian", "05:45 total depo"
]

JADWAL_MAP = {
    "pagi": JADWAL_PAGI,
    "siang": JADWAL_SIANG,
    "malam": JADWAL_MALAM,
}

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("JADWAL PAGI", callback_data="jadwal_pagi")],
        [InlineKeyboardButton("JADWAL SIANG", callback_data="jadwal_siang")],
        [InlineKeyboardButton("JADWAL MALAM", callback_data="jadwal_malam")],
        [InlineKeyboardButton("Reset Tugas Hari Ini", callback_data="reset_tugas")],
    ])

def jadwal_keyboard(jadwal_list, done_set):
    buttons = []
    for idx, item in enumerate(jadwal_list):
        checked = "✅" if idx in done_set else "⬜"
        buttons.append([InlineKeyboardButton(f"{checked} {item}", callback_data=f"toggle_done:{idx}")])
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Pilih jadwal yang ingin diaktifkan / dilihat:",
        reply_markup=main_menu_keyboard()
    )

async def reset_tugas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_data = context.chat_data
    for key in ["done_pagi", "done_siang", "done_malam"]:
        chat_data[key] = set()
    await update.message.reply_text("✅ Semua tugas sudah direset. Siap digunakan kembali untuk hari berikutnya.")

async def waktu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(TIMEZONE)
    await update.message.reply_text(f"Waktu server sekarang:\n{now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_data = context.chat_data
    data = query.data

    if data == "back_to_menu":
        await query.edit_message_text("Pilih jadwal yang ingin diaktifkan / dilihat:", reply_markup=main_menu_keyboard())
        return

    if data == "reset_tugas":
        for key in ["done_pagi", "done_siang", "done_malam"]:
            chat_data[key] = set()
        await query.edit_message_text("✅ Semua tugas sudah direset. Siap digunakan kembali untuk hari berikutnya.", reply_markup=main_menu_keyboard())
        return

    if data.startswith("jadwal_"):
        jadwal_key = data.split("_")[1]
        chat_data["active_jadwal"] = jadwal_key
        done_set = chat_data.setdefault(f"done_{jadwal_key}", set())
        jadwal_list = JADWAL_MAP[jadwal_key]
        await query.edit_message_text(
            f"JADWAL {jadwal_key.upper()}:\n\n" + "\n".join(
                f"{'✅' if idx in done_set else '⬜'} {item}" for idx, item in enumerate(jadwal_list)
            ),
            reply_markup=jadwal_keyboard(jadwal_list, done_set)
        )
        return

    if data.startswith("toggle_done:"):
        idx = int(data.split(":")[1])
        jadwal_key = chat_data.get("active_jadwal")
        if not jadwal_key:
            await query.answer("Pilih jadwal dulu ya.", show_alert=True)
            return
        done_set = chat_data.setdefault(f"done_{jadwal_key}", set())
        if idx in done_set:
            done_set.remove(idx)
        else:
            done_set.add(idx)
        jadwal_list = JADWAL_MAP[jadwal_key]
        await query.edit_message_text(
            f"JADWAL {jadwal_key.upper()}:\n\n" + "\n".join(
                f"{'✅' if i in done_set else '⬜'} {it}" for i, it in enumerate(jadwal_list)
            ),
            reply_markup=jadwal_keyboard(jadwal_list, done_set)
        )
        return

def parse_time_from_task(task_text):
    # Extract HH and MM from string like "07:05 cek link pc indo"
    try:
        time_part = task_text.split()[0]
        hh, mm = time_part.split(":")
        return int(hh), int(mm)
    except Exception as e:
        logger.warning(f"Error parsing time from '{task_text}': {e}")
        return None, None

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    jadwal_list = job.data.get("jadwal_list")
    item_idx = job.data.get("item_idx")
    task_text = jadwal_list[item_idx]

    await context.bot.send_message(chat_id, f"⏰ Reminder: {task_text}")

async def schedule_jobs(application):
    # Hapus semua job lama dulu
    for job in application.job_queue.get_jobs_by_name("reminder"):
        job.schedule_removal()

    # Untuk setiap chat yang punya aktif jadwal, schedule ulang
    async with application.persistence_lock:
        chat_data_all = application.persistence._dict.get("chat_data", {})
        for chat_id_str, chat_data in chat_data_all.items():
            chat_id = int(chat_id_str)
            active_jadwal = chat_data.get("active_jadwal")
            if not active_jadwal:
                continue
            done_set = chat_data.get(f"done_{active_jadwal}", set())
            jadwal_list = JADWAL_MAP[active_jadwal]
            now = datetime.datetime.now(TIMEZONE)
            for idx, task in enumerate(jadwal_list):
                if idx in done_set:
                    continue
                hh, mm = parse_time_from_task(task)
                if hh is None:
                    continue
                # Set waktu reminder 5 menit sebelum jadwal (bisa diubah)
                reminder_time = now.replace(hour=hh, minute=mm, second=0, microsecond=0) - datetime.timedelta(minutes=5)
                if reminder_time < now:
                    # kalau sudah lewat hari ini, skip
                    continue
                application.job_queue.run_once(
                    send_reminder,
                    when=(reminder_time - now).total_seconds(),
                    chat_id=chat_id,
                    name="reminder",
                    data={"jadwal_list": jadwal_list, "item_idx": idx}
                )


async def on_startup(app):
    logger.info("Starting webhook server...")
    # Schedule ulang semua job reminder setiap kali bot start
    await schedule_jobs(app["bot_app"])

async def on_shutdown(app):
    logger.info("Shutting down webhook server...")

async def webhook_handler(request):
    bot_app = request.app["bot_app"]
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.update_queue.put(update)
    return web.Response(text="OK")

async def daily_reset_job(context: ContextTypes.DEFAULT_TYPE):
    # Reset semua done_set setiap hari jam 00:01
    chat_data_all = context.application.persistence._dict.get("chat_data", {})
    for chat_id_str, chat_data in chat_data_all.items():
        for key in ["done_pagi", "done_siang", "done_malam"]:
            chat_data[key] = set()
    logger.info("Reset semua tugas harian berhasil.")

async def main():
    application = ApplicationBuilder()\
        .token(TOKEN)\
        .persistence(persistence)\
        .build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_tugas))
    application.add_handler(CommandHandler("waktu", waktu))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Schedule reset harian jam 00:01
    application.job_queue.run_daily(daily_reset_job, time=datetime.time(hour=0, minute=1, tzinfo=TIMEZONE))

    # Jalankan webhook server aiohttp
    app = web.Application()
    app["bot_app"] = application
    app.router.add_post(WEBHOOK_PATH, webhook_handler)

    # Set webhook
    await application.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set at {WEBHOOK_URL}")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Server started at port {PORT}")

    # Run bot sampai ctrl+c / termination
    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # Optional fallback polling if webhook down
    await application.updater.idle()
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
