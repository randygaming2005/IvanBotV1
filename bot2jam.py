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
from apscheduler.jobstores.base import JobLookupError  # Untuk menangani job yang sudah dihapus

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN") or "YOUR_BOT_TOKEN_HERE"
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None

persistence = PicklePersistence(filepath="reminder_data.pkl")
user_jobs = {}  # Menyimpan daftar JobQueue per chat_id
timezone = pytz.timezone("Asia/Jakarta")

# -------------------------------------------------
# Definisi jadwal pengingat (5 menit sebelum waktu target)
# -------------------------------------------------
REMINDER_SECTIONS = {
    "Pagi": [
        (7, 5,  "07:05 cek link pc indo"),
        (7, 0,  "07:00 cek phising"),
        (7, 5,  "07:05 cek dana PGA BL"),
        (7, 15, "07:15 req dana PGA"),
        (7, 30, "07:30 paito berita"),
        (8, 0,  "08:00 total depo"),
        (8, 0,  "08:00 Slot Harian"),
        (8, 0,  "08:00 jadwalkan bukti jp ke jam 10.00"),
        (8, 10, "08:10 BC link alternatif ke jam 12.00"),
        (9, 0,  "09:00 jowo pools"),
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
        (12, 50,"12:50 live ttm"),
        (12, 30,"12:30 cek phising"),
        (13, 0, "13:00 wd report"),
        (13, 0, "13:00 BC Result Toto Macau"),
        (13, 30,"13:30 slot & rng harian"),
        (14, 0, "14:00 BC Result Sydney"),
        (14, 0, "14:00 depo harian"),
    ],
    "Siang": [
        (15, 30,"15:30 cek link"),
        (16, 0, "16:00 cek phising"),
        (16, 0, "16:00 deposit harian"),
        (16, 30,"16:30 jadwalkan bukti jp ke jam 17.00"),
        (16, 0, "16:00 isi data selisih"),
        (16, 0, "16:00 BC Result Toto Macau"),
        (17, 40,"17:40 SLOT harian (kalau tidak ada sgp jam 18.30)"),
        (17, 50,"17:50 BC Result Singapore"),
        (18, 0, "18:00 5 lucky ball"),
        (18, 0, "18:00 deposit harian"),
        (18, 5, "18:05 BC link alt ke jam 19.00"),
        (18, 10,"18:10 isi data wlb2c"),
        (19, 0, "19:00 BC Result Toto Macau"),
        (19, 30,"19:30 Audit BCA"),
        (19, 45,"19:45 First Register"),
        (20, 0, "20:00 deposit harian"),
        (21, 0, "21:00 jowo pools"),
        (21, 0, "21:00 cek phising"),
        (21, 0, "21:00 wd report"),
        (22, 0, "22:00 BC Result Toto Macau"),
        (22, 0, "22:00 deposit harian"),
        (22, 45,"22:45 Slot harian"),
    ],
    "Malam": [
        (23, 0, "23:00 SLOT harian"),
        (23, 10,"23:10 BC Result Hongkong"),
        (23, 30,"23:30 cek link & cek phising"),
        (23, 30,"23:30 BC rtp slot jam 00.10"),
        (23, 40,"23:40 depo harian"),
        (0, 5,  "00:05 BC Result Toto Macau"),
        (0, 1,  "00:01 update total bonus"),
        (0, 30, "00:30 BC link alt jam 5"),
        (0, 30, "00:30 BC bukti JP jam 4"),
        (0, 30, "00:30 BC maintenance mingguan ke jam 4 (kamis)"),
        (0, 45, "00:45 slot harian"),
        (1, 0,  "01:00 isi biaya pulsa / isi akuran (senin subuh)"),
        (1, 30, "01:30 isi data promo"),
        (2, 0,  "02:00 total depo"),
        (2, 0,  "02:00 cek pl config"),
        (3, 30, "03:30 Audit BCA"),
        (3, 45, "03:45 First Register"),
        (4, 0,  "04:00 total depo"),
        (5, 0,  "05:00 cek phising"),
        (5, 0,  "05:00 wd report"),
        (5, 0,  "05:00 Slot harian"),
        (5, 45, "05:45 total depo"),
    ],
}

# -------------------------------------------------
# Fungsi untuk mengirim pesan reminder
# -------------------------------------------------
async def reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    message = data.get("message")
    section = data.get("section")
    thread_id = data.get("thread_id")

    # Cek apakah pesan ini sudah ditandai selesai
    completed_tasks = context.bot_data.get("completed_tasks", {}).get(chat_id, set())
    if message in completed_tasks:
        return

    # Cek apakah section masih aktif
    active_sections = context.bot_data.get("active_sections", {}).get(chat_id, {})
    if not active_sections.get(section):
        return

    # Kirim reminder
    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=f"🔔 {message}"
    )

# -------------------------------------------------
# Handler /start, membuat tombol untuk pilih section
# -------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Pagi", callback_data="section_Pagi")],
        [InlineKeyboardButton("Siang", callback_data="section_Siang")],
        [InlineKeyboardButton("Malam", callback_data="section_Malam")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🕒 Pilih bagian jadwal untuk dikendalikan:", reply_markup=reply_markup)

# -------------------------------------------------
# Handler ketika user memilih salah satu section
# -------------------------------------------------
async def section_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_")[1]
    chat_id = query.message.chat.id

    completed = context.bot_data.get("completed_tasks", {}).get(chat_id, set())

    # Membangun teks beserta inline keyboard untuk satu section
    lines = [f"📋 Jadwal *{section}*:"]
    keyboard = [
        [InlineKeyboardButton("✅ Aktifkan", callback_data=f"activate_{section}")]
    ]
    for h, m, msg in REMINDER_SECTIONS[section]:
        status = "✅" if msg in completed else "❌"
        lines.append(f"{status} {h:02d}:{m:02d} - {msg}")
        keyboard.append([InlineKeyboardButton(f"{status} {h:02d}:{m:02d} - {msg}", callback_data=f"done_{section}_{msg}")])
    keyboard.append([InlineKeyboardButton("❌ Reset", callback_data=f"reset_{section}")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="go_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=reply_markup)

# -------------------------------------------------
# Handler untuk mengaktifkan section (menjadwalkan reminder)
# -------------------------------------------------
async def activate_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_")[1]
    chat_id = query.message.chat.id

    # Tandai section sebagai aktif
    context.bot_data.setdefault("active_sections", {}).setdefault(chat_id, {})[section] = True

    # Jadwalkan reminder untuk seluruh entry di section tersebut
    await schedule_section_reminders(context.application, chat_id, section)

    await query.edit_message_text(
        f"✅ Pengingat untuk bagian *{section}* telah diaktifkan.",
        parse_mode='Markdown'
    )

# -------------------------------------------------
# Handler untuk mereset section (menghapus semua job, menonaktifkan, dan menghapus tanda ✅)
# -------------------------------------------------
async def reset_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_")[1]
    chat_id = query.message.chat.id

    # Hentikan semua job yang berhubungan dengan section ini
    if chat_id in user_jobs:
        for job in user_jobs[chat_id][:]:
            job_data = job.data or {}
            if job_data.get("section") == section:
                try:
                    job.schedule_removal()
                except JobLookupError:
                    # Job sudah terhapus dari scheduler, abaikan
                    pass
                user_jobs[chat_id].remove(job)

    # Nonaktifkan section
    if "active_sections" in context.bot_data and chat_id in context.bot_data["active_sections"]:
        context.bot_data["active_sections"][chat_id].pop(section, None)

    # Hapus semua tanda ✅ untuk pesan di section ini
    completed = context.bot_data.setdefault("completed_tasks", {}).setdefault(chat_id, set())
    for _, _, msg in REMINDER_SECTIONS[section]:
        completed.discard(msg)

    # Tampilkan ulang daftar jadwal; semua status kembali ke ❌
    await section_handler(update, context)

# -------------------------------------------------
# Handler untuk menandai sebuah pesan sudah selesai (done/tidak done)
# -------------------------------------------------
async def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, section, msg = query.data.split("_", 2)
    chat_id = query.message.chat.id

    context.bot_data.setdefault("completed_tasks", {}).setdefault(chat_id, set())

    if msg in context.bot_data["completed_tasks"][chat_id]:
        context.bot_data["completed_tasks"][chat_id].remove(msg)
    else:
        context.bot_data["completed_tasks"][chat_id].add(msg)

    # Tampilkan ulang daftar jadwal untuk section itu dengan status terbaru
    await section_handler(update, context)

# -------------------------------------------------
# Handler “Kembali” (untuk kembali ke menu utama /start)
# -------------------------------------------------
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(query, context)

# -------------------------------------------------
# Fungsi utama untuk menjadwalkan semua reminder di satu section
# -------------------------------------------------
async def schedule_section_reminders(application: ApplicationBuilder, chat_id: int, section: str, thread_id=None):
    """
    Untuk setiap (jam, menit, pesan) di REMINDER_SECTIONS[section],
    hitung waktu pengingat 5 menit sebelum, konversi ke UTC, lalu run_daily.
    """
    job_queue = application.job_queue

    # Pastikan ada list di user_jobs
    user_jobs.setdefault(chat_id, [])

    for hour, minute, message in REMINDER_SECTIONS[section]:
        # Ambil waktu sekarang di zona Asia/Jakarta, lalu set jam & menit target
        now_local = datetime.datetime.now(timezone)
        target_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Kurangi 5 menit untuk pengingat
        reminder_local = target_local - datetime.timedelta(minutes=5)

        # Jika jamnya bergeser ke hari sebelumnya (misalnya target jam 00:03),
        # kita lakukan localize agar ada tzinfo:
        if reminder_local.tzinfo is None:
            reminder_local = timezone.localize(reminder_local)

        # Konversi ke UTC
        reminder_utc_time = reminder_local.astimezone(pytz.utc).time()

        job_name = f"reminder_{chat_id}_{section}_{hour:02d}{minute:02d}"

        # Hapus job lama jika sudah ada
        for old_job in job_queue.get_jobs_by_name(job_name):
            old_job.schedule_removal()

        # Jadwalkan job dengan fungsi 'reminder'
        job = job_queue.run_daily(
            reminder,
            time=reminder_utc_time,
            name=job_name,
            data={
                "chat_id": chat_id,
                "message": message,
                "section": section,
                "thread_id": thread_id
            }
        )

        user_jobs[chat_id].append(job)

# -------------------------------------------------
# Handler untuk melihat daftar section yang aktif beserta isi jadwalnya (/jadwalaktif)
# -------------------------------------------------
async def jadwal_aktif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    active_dict = context.bot_data.get("active_sections", {}).get(chat_id, {})

    # Cari section yang sedang aktif (value == True)
    aktif_sections = [sec for sec, val in active_dict.items() if val]

    if not aktif_sections:
        # Jika tidak ada section aktif
        await update.message.reply_text("ℹ️ Tidak ada jadwal yang sedang aktif.")
        return

    # Untuk setiap section aktif, kirim satu pesan dengan detail jadwal dan tombol interaktif
    for section in aktif_sections:
        completed = context.bot_data.get("completed_tasks", {}).get(chat_id, set())

        # Bangun header teks
        lines = [f"📋 Jadwal *{section}* (Aktif):"]
        keyboard = []
        for h, m, msg in REMINDER_SECTIONS[section]:
            status = "✅" if msg in completed else "❌"
            lines.append(f"{status} {h:02d}:{m:02d} - {msg}")
            # Tombol untuk toggle done/undone
            keyboard.append([InlineKeyboardButton(f"{status} {h:02d}:{m:02d} - {msg}", callback_data=f"done_{section}_{msg}")])

        # Tambahkan tombol Reset pada bagian bawah
        keyboard.append([InlineKeyboardButton(f"❌ Reset {section}", callback_data=f"reset_{section}")])
        # Tombol kembali ke menu utama
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="go_back")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=reply_markup)

# -------------------------------------------------
# Handler untuk error (jika terjadi exception)
# -------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("❗ Exception occurred:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, text="⚠️ Terjadi kesalahan. Silakan coba lagi nanti.")
        except Exception:
            pass

# -------------------------------------------------
# JobQueue dijalankan setelah bot dijalankan
# -------------------------------------------------
async def start_jobqueue(application):
    await application.job_queue.start()

# -------------------------------------------------
# Handler untuk endpoint root (cek bot running)
# -------------------------------------------------
async def handle_root(request):
    return web.Response(text="Bot is running")

# -------------------------------------------------
# Handler untuk webhook Telegram
# -------------------------------------------------
async def handle_webhook(request):
    application = request.app["application"]
    update = await request.json()
    from telegram import Update as TgUpdate
    tg_update = TgUpdate.de_json(update, application.bot)
    await application.update_queue.put(tg_update)
    return web.Response()

# -------------------------------------------------
# Tambahan command baru: /reset (reset semua reminder + data)
# -------------------------------------------------
async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Hentikan semua job untuk user ini
    if chat_id in user_jobs:
        for job in user_jobs[chat_id]:
            try:
                job.schedule_removal()
            except JobLookupError:
                pass
        user_jobs[chat_id].clear()

    # Reset bot_data: active_sections & completed_tasks
    if "active_sections" in context.bot_data and chat_id in context.bot_data["active_sections"]:
        context.bot_data["active_sections"][chat_id].clear()

    if "completed_tasks" in context.bot_data and chat_id in context.bot_data["completed_tasks"]:
        context.bot_data["completed_tasks"][chat_id].clear()

    await update.message.reply_text("🔄 Semua tugas dan pengingat telah direset dan siap digunakan kembali.")

# -------------------------------------------------
# Fungsi pembantu untuk menampilkan daftar jadwal + status (✅/❌) per section (digunakan oleh /jadwlpagi, /jadwalsiang, /jadwalmalam)
# -------------------------------------------------
def format_jadwal(chat_id, section, context):
    completed = context.bot_data.get("completed_tasks", {}).get(chat_id, set())
    lines = [f"📋 Jadwal *{section}*:"]
    for h, m, msg in REMINDER_SECTIONS[section]:
        status = "✅" if msg in completed else "❌"
        lines.append(f"{status} {h:02d}:{m:02d} - {msg}")
    return "\n".join(lines)

async def jadwal_pagi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = format_jadwal(chat_id, "Pagi", context)
    await update.message.reply_text(text, parse_mode="Markdown")

async def jadwal_siang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = format_jadwal(chat_id, "Siang", context)
    await update.message.reply_text(text, parse_mode="Markdown")

async def jadwal_malam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = format_jadwal(chat_id, "Malam", context)
    await update.message.reply_text(text, parse_mode="Markdown")

# -------------------------------------------------
# Fungsi main: membangun aplikasi, menambahkan handler, dan menjalankan webhook/server
# -------------------------------------------------
async def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    # Tambahkan handler perintah
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_all))
    application.add_handler(CommandHandler("jadwlpagi", jadwal_pagi))
    application.add_handler(CommandHandler("jadwalsiang", jadwal_siang))
    application.add_handler(CommandHandler("jadwalmalam", jadwal_malam))
    application.add_handler(CommandHandler("jadwalaktif", jadwal_aktif))

    # Tambahkan handler CallbackQuery (tombol interaktif)
    application.add_handler(CallbackQueryHandler(section_handler, pattern="^section_"))
    application.add_handler(CallbackQueryHandler(activate_section, pattern="^activate_"))
    application.add_handler(CallbackQueryHandler(reset_section, pattern="^reset_"))
    application.add_handler(CallbackQueryHandler(mark_done, pattern="^done_"))
    application.add_handler(CallbackQueryHandler(go_back, pattern="^go_back$"))

    application.add_error_handler(error_handler)

    # Jalankan inisialisasi & start bot Telegram
    await application.initialize()
    await application.start()

    # Setelah bot Telegram berjalan, jalankan JobQueue
    await start_jobqueue(application)

    # Siapkan aiohttp untuk webhook (jika menggunakan metode webhook)
    app = web.Application()
    app["application"] = application
    app.add_routes([
        web.get("/", handle_root),
        web.post(WEBHOOK_PATH, handle_webhook),
    ])

    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
    else:
        logging.warning("⚠️ WEBHOOK_URL_BASE environment variable tidak diset, webhook tidak aktif!")

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Agar proses tidak langsung berhenti
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())