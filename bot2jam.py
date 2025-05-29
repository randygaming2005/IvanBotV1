import logging
import os
import datetime
import pytz
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, PicklePersistence
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = os.environ.get("TOKEN") or "YOUR_BOT_TOKEN"
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None

timezone = pytz.timezone("Asia/Jakarta")
persistence = PicklePersistence(filepath="data.pkl")

# Jadwal Tugas
JADWAL = {
    "pagi": [
        ("07:00", "cek phising"), ("07:05", "cek link pc indo"),
        ("08:00", "total depo"), ("10:00", "cek data selisih"),
    ],
    "siang": [
        ("15:30", "cek link"), ("16:00", "deposit harian"),
        ("18:00", "5 lucky ball"), ("20:00", "deposit harian"),
    ],
    "malam": [
        ("23:00", "SLOT harian"), ("00:01", "update total bonus"),
        ("02:00", "total depo"), ("05:00", "cek phising"),
    ],
}

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("JADWAL PAGI", callback_data="jadwal_pagi")],
        [InlineKeyboardButton("JADWAL SIANG", callback_data="jadwal_siang")],
        [InlineKeyboardButton("JADWAL MALAM", callback_data="jadwal_malam")],
    ])

def jadwal_keyboard(jadwal_list, done_set):
    buttons = [
        [InlineKeyboardButton(f"{'✅' if idx in done_set else ''} {item}", callback_data=f"toggle_done:{idx}")]
        for idx, item in enumerate(jadwal_list)
    ]
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(buttons)

def format_jadwal(jadwal_list, done_set):
    return "\n".join([
        f"{'✅' if idx in done_set else '⬜'} {item}" for idx, item in enumerate(jadwal_list)
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.bot_data["chat_id"] = chat_id
    await update.message.reply_text("Halo! Silakan pilih jadwal yang ingin dilihat:", reply_markup=main_menu_keyboard())

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data.pop("done_pagi", None)
    context.chat_data.pop("done_siang", None)
    context.chat_data.pop("done_malam", None)
    await update.message.reply_text("✅ Semua tugas telah direset.")

async def waktu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(timezone)
    await update.message.reply_text(f"Waktu server sekarang:\n{now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_data = context.chat_data

    if data == "back_to_menu":
        await query.edit_message_text("Silakan pilih jadwal yang ingin dilihat:", reply_markup=main_menu_keyboard())
        return

    if data.startswith("jadwal_"):
        sesi = data.split("_")[1]
        chat_data["current_jadwal"] = sesi
        tugas_list = [item[1] for item in JADWAL[sesi]]
        done_set = chat_data.setdefault(f"done_{sesi}", set())
        await query.edit_message_text(
            f"JADWAL {sesi.upper()}:\n\n" + format_jadwal(tugas_list, done_set),
            reply_markup=jadwal_keyboard(tugas_list, done_set),
        )

    if data.startswith("toggle_done:"):
        idx = int(data.split(":")[1])
        sesi = chat_data.get("current_jadwal")
        if not sesi:
            await query.answer("Pilih jadwal dulu.", show_alert=True)
            return

        key = f"done_{sesi}"
        done_set = chat_data.setdefault(key, set())
        if idx in done_set:
            done_set.remove(idx)
        else:
            done_set.add(idx)

        tugas_list = [item[1] for item in JADWAL[sesi]]
        await query.edit_message_text(
            f"JADWAL {sesi.upper()}:\n\n" + format_jadwal(tugas_list, done_set),
            reply_markup=jadwal_keyboard(tugas_list, done_set),
        )

async def kirim_pengingat(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    tugas = job.data
    chat_id = job.chat_id
    await context.bot.send_message(chat_id=chat_id, text=f"⏰ Pengingat: {tugas}")

def schedule_all_jobs(application):
    chat_id = application.bot_data.get("chat_id")
    if not chat_id:
        logging.warning("Chat ID belum tersedia. Jalankan /start dulu.")
        return

    for sesi, daftar in JADWAL.items():
        for waktu_str, tugas in daftar:
            jam, menit = map(int, waktu_str.split(":"))
            waktu_tugas = datetime.time(hour=jam, minute=menit, tzinfo=timezone)
            pengingat_waktu = (datetime.datetime.combine(datetime.date.today(), waktu_tugas) - datetime.timedelta(minutes=5)).time()

            application.job_queue.run_daily(
                callback=kirim_pengingat,
                time=pengingat_waktu,
                chat_id=chat_id,
                name=f"{sesi}_{tugas}",
                data=tugas
            )
            logging.info(f"Dijadwalkan pengingat: {tugas} pukul {pengingat_waktu}")

async def aktifkan_pengingat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.bot_data["chat_id"] = chat_id
    schedule_all_jobs(context.application)
    await update.message.reply_text("✅ Pengingat aktif. Bot akan mengirim notifikasi 5 menit sebelum tiap tugas.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Exception:", exc_info=context.error)

# Webhook handlers
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
        ApplicationBuilder().token(TOKEN).persistence(persistence).build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("waktu", waktu))
    application.add_handler(CommandHandler("aktifkan_pengingat", aktifkan_pengingat))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    app = web.Application()
    app["application"] = application
    app.add_routes([web.get("/", handle_root), web.post(WEBHOOK_PATH, handle_webhook)])

    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")

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
