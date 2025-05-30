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
    CallbackQueryHandler,
    ContextTypes,
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
timezone = pytz.timezone("Asia/Jakarta")
user_active_sections = {}

# Menyimpan status tugas per user, section, dan tugas
user_task_status = {}  # { chat_id: { section: { (h,m,msg): bool } } }

REMINDER_SECTIONS = {
    "Pagi": [
        (7, 5, "07:05 cek link pc indo"),
        (7, 0, "07:00 cek phising"),
        (7, 5, "07:05 cek dana PGA BL"),
        (7, 15, "07:15 req dana PGA"),
        (7, 30, "07:30 paito berita"),
        (8, 0, "08:00 total depo"),
        (8, 0, "08:00 Slot Harian"),
        (8, 0, "08:00 jadwalkan bukti jp ke jam 10.00"),
        (8, 10, "08:10 BC link alternatif ke jam 12.00"),
        (9, 0, "09:00 jowo pools"),
        (9, 10, "09:10 TO semua pasaran"),
        (9, 30, "09:30 Audit BCA"),
        (9, 45, "09:45 First Register"),
        (10, 0, "10:00 BC maintenance done (kamis)"),
        (10, 0, "10:00 cek data selisih"),
        (10, 0, "10:00 total depo"),
        (10, 30, "10:30 isi data bola (> jam 1)"),
        (11, 0, "11:00 bc maintenance WL (selasa)"),
        (11, 0, "11:00 bc jadwal bola"),
        (12, 0, "12:00 total depo"),
        (12, 0, "12:00 slot & rng mingguan"),
        (12, 50, "12:50 live ttm"),
        (12, 30, "12:30 cek phising"),
        (13, 0, "13:00 wd report"),
        (13, 0, "13:00 BC Result Toto Macau"),
        (13, 30, "13:30 slot & rng harian"),
        (14, 0, "14:00 BC Result Sydney"),
        (14, 0, "14:00 depo harian"),
    ],
    "Siang": [
        (15, 30, "15:30 cek link"),
        (16, 0, "16:00 cek phising"),
        (16, 0, "16:00 deposit harian"),
        (16, 30, "16:30 jadwalkan bukti jp ke jam 17.00"),
        (16, 0, "16:00 isi data selisih"),
        (16, 0, "16:00 BC Result Toto Macau"),
        (17, 40, "17:40 SLOT harian (kalau tidak ada sgp jam 18.30)"),
        (17, 50, "17:50 BC Result Singapore"),
        (18, 0, "18:00 5 lucky ball"),
        (18, 0, "18:00 deposit harian"),
        (18, 5, "18:05 BC link alt ke jam 19.00"),
        (18, 10, "18:10 isi data wlb2c"),
        (19, 0, "19:00 BC Result Toto Macau"),
        (19, 30, "19:30 Audit BCA"),
        (19, 45, "19:45 First Register"),
        (20, 0, "20:00 deposit harian"),
        (21, 0, "21:00 jowo pools"),
        (21, 0, "21:00 cek phising"),
        (21, 0, "21:00 wd report"),
        (22, 0, "22:00 BC Result Toto Macau"),
        (22, 0, "22:00 deposit harian"),
        (22, 45, "22:45 Slot harian"),
    ],
    "Malam": [
        (23, 0, "23:00 SLOT harian"),
        (23, 10, "23:10 BC Result Hongkong"),
        (23, 30, "23:30 cek link & cek phising"),
        (23, 30, "23:30 BC rtp slot jam 00.10"),
        (23, 40, "23:40 depo harian"),
        (0, 5, "00:05 BC Result Toto Macau"),
        (0, 1, "00:01 update total bonus"),
        (0, 30, "00:30 BC link alt jam 5"),
        (0, 30, "00:30 BC bukti JP jam 4"),
        (0, 30, "00:30 BC maintenance mingguan ke jam 4 (kamis)"),
        (0, 45, "00:45 slot harian"),
        (1, 0, "01:00 isi biaya pulsa / isi akuran (senin subuh)"),
        (1, 30, "01:30 isi data promo"),
        (2, 0, "02:00 total depo"),
        (2, 0, "02:00 cek pl config"),
        (3, 30, "03:30 Audit BCA"),
        (3, 45, "03:45 First Register"),
        (4, 0, "04:00 total depo"),
        (5, 0, "05:00 cek phising"),
        (5, 0, "05:00 wd report"),
        (5, 0, "05:00 Slot harian"),
        (5, 45, "05:45 total depo"),
    ],
}

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    message = data["message"]
    section = data["section"]
    thread_id = data.get("thread_id")

    # Cek apakah tugas sudah diceklis (selesai)
    status_dict = user_task_status.get(chat_id, {}).get(section, {})
    key = None
    for k in status_dict:
        if k[2] == message:
            key = k
            break

    if key and status_dict.get(key, False):
        # Tugas sudah diceklis, jangan ingatkan
        return

    if not user_active_sections.get(chat_id, {}).get(section):
        return

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=f"🔔 {message}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Pagi", callback_data="section_Pagi")],
        [InlineKeyboardButton("Siang", callback_data="section_Siang")],
        [InlineKeyboardButton("Malam", callback_data="section_Malam")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🕒 Pilih bagian jadwal untuk dikendalikan:", reply_markup=reply_markup)

async def section_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    section = query.data.split("_")[1]
    chat_id = query.message.chat.id

    # Inisialisasi status tugas jika belum ada
    if chat_id not in user_task_status:
        user_task_status[chat_id] = {}
    if section not in user_task_status[chat_id]:
        user_task_status[chat_id][section] = {(h, m, msg): False for h, m, msg in REMINDER_SECTIONS[section]}

    keyboard = [
        [InlineKeyboardButton("✅ Aktifkan", callback_data=f"activate_{section}")],
    ]

    for h, m, msg in REMINDER_SECTIONS[section]:
        done = user_task_status[chat_id][section].get((h, m, msg), False)
        icon = "✅" if done else "❌"
        callback_data = f"toggle_{section}_{h}_{m}"
        keyboard.append([InlineKeyboardButton(f"{icon} {h:02d}:{m:02d} - {msg}", callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("❌ Reset", callback_data=f"reset_{section}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"📋 Jadwal {section}:\n"
    await query.edit_message_text(text=text, reply_markup=reply_markup)

async def toggle_task_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    section = data[1]
    h = int(data[2])
    m = int(data[3])
    chat_id = query.message.chat.id

    if chat_id not in user_task_status:
        user_task_status[chat_id] = {}
    if section not in user_task_status[chat_id]:
        user_task_status[chat_id][section] = {(hh, mm, msg): False for hh, mm, msg in REMINDER_SECTIONS[section]}

    task_key = None
    for hh, mm, msg in REMINDER_SECTIONS[section]:
        if hh == h and mm == m:
            task_key = (hh, mm, msg)
            break

    if task_key is None:
        return

    current_status = user_task_status[chat_id][section].get(task_key, False)
    user_task_status[chat_id][section][task_key] = not current_status

    # Refresh tampilan
    keyboard = [
        [InlineKeyboardButton("✅ Aktifkan", callback_data=f"activate_{section}")],
    ]
    for hh, mm, msg in REMINDER_SECTIONS[section]:
        done = user_task_status[chat_id][section].get((hh, mm, msg), False)
        icon = "✅" if done else "❌"
        callback_data = f"toggle_{section}_{hh}_{mm}"
        keyboard.append([InlineKeyboardButton(f"{icon} {hh:02d}:{mm:02d} - {msg}", callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("❌ Reset", callback_data=f"reset_{section}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"📋 Jadwal {section}:\n"
    await query.edit_message_text(text=text, reply_markup=reply_markup)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Pagi", callback_data="section_Pagi")],
        [InlineKeyboardButton("Siang", callback_data="section_Siang")],
        [InlineKeyboardButton("Malam", callback_data="section_Malam")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🕒 Pilih bagian jadwal untuk dikendalikan:", reply_markup=reply_markup)

async def activate_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_")[1]
    chat_id = query.message.chat.id

    if chat_id not in user_active_sections:
        user_active_sections[chat_id] = {}

    user_active_sections[chat_id][section] = True
    await schedule_section_reminders(context.application, chat_id, section)
    await query.edit_message_text(f"✅ Pengingat untuk bagian *{section}* telah diaktifkan.", parse_mode='Markdown')

async def reset_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_")[1]
    chat_id = query.message.chat.id

    # Reset status checklist ke False
    if chat_id in user_task_status and section in user_task_status[chat_id]:
        for k in user_task_status[chat_id][section]:
            user_task_status[chat_id][section][k] = False

    await query.edit_message_text(f"❌ Checklist untuk bagian *{section}* sudah direset.", parse_mode='Markdown')

async def schedule_section_reminders(application, chat_id: int, section: str):
    # Hapus job lama untuk user dan section ini
    job_name_prefix = f"reminder_{chat_id}_{section}_"
    existing_jobs = [job for job in application.job_queue.get_jobs_by_name(job_name_prefix)]
    for job in existing_jobs:
        job.schedule_removal()

    now = datetime.datetime.now(tz=timezone)

    for h, m, msg in REMINDER_SECTIONS[section]:
        # Hitung waktu pengingat berikutnya
        remind_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if remind_time < now:
            remind_time += datetime.timedelta(days=1)

        delta = (remind_time - now).total_seconds()

        job_name = f"{job_name_prefix}{h:02d}{m:02d}"

        application.job_queue.run_once(
            reminder,
            when=delta,
            data={"chat_id": chat_id, "message": msg, "section": section},
            name=job_name,
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Gunakan /start untuk memulai dan memilih jadwal yang ingin diaktifkan.")

def main():
    application = ApplicationBuilder().token(TOKEN).persistence(persistence).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(section_handler, pattern=r"^section_"))
    application.add_handler(CallbackQueryHandler(toggle_task_status, pattern=r"^toggle_"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern=r"^back_main$"))
    application.add_handler(CallbackQueryHandler(activate_section, pattern=r"^activate_"))
    application.add_handler(CallbackQueryHandler(reset_section, pattern=r"^reset_"))

    # Jika kamu ingin pakai polling
    application.run_polling()

if __name__ == "__main__":
    main()
